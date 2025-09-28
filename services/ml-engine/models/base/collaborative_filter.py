import torch
import torch.nn as nn
from typing import List, Dict, Tuple
from uuid import UUID
import numpy as np
from scipy.sparse import csr_matrix
from sklearn.decomposition import TruncatedSVD
import pickle


class CollaborativeFilter(nn.Module):
    def __init__(self, num_users: int, num_tracks: int, embedding_dim: int = 64):
        super().__init__()
        self.num_users = num_users
        self.num_tracks = num_tracks
        self.embedding_dim = embedding_dim

        self.user_embeddings = nn.Embedding(num_users, embedding_dim)
        self.track_embeddings = nn.Embedding(num_tracks, embedding_dim)

        self.user_bias = nn.Embedding(num_users, 1)
        self.track_bias = nn.Embedding(num_tracks, 1)
        self.global_bias = nn.Parameter(torch.zeros(1))

        self._init_weights()

    def _init_weights(self):
        nn.init.normal_(self.user_embeddings.weight, std=0.01)
        nn.init.normal_(self.track_embeddings.weight, std=0.01)
        nn.init.zeros_(self.user_bias.weight)
        nn.init.zeros_(self.track_bias.weight)

    def forward(self, user_ids: torch.Tensor, track_ids: torch.Tensor) -> torch.Tensor:
        user_emb = self.user_embeddings(user_ids)
        track_emb = self.track_embeddings(track_ids)

        dot_product = (user_emb * track_emb).sum(dim=1, keepdim=True)

        user_b = self.user_bias(user_ids)
        track_b = self.track_bias(track_ids)

        prediction = dot_product + user_b + track_b + self.global_bias

        return prediction.squeeze()

    def predict(self, user_id: int, track_ids: List[int]) -> np.ndarray:
        self.eval()
        with torch.no_grad():
            user_tensor = torch.tensor([user_id] * len(track_ids), dtype=torch.long)
            track_tensor = torch.tensor(track_ids, dtype=torch.long)
            scores = self.forward(user_tensor, track_tensor)
            return scores.cpu().numpy()

    def recommend(self, user_id: int, k: int = 20, exclude_tracks: List[int] = None) -> List[Tuple[int, float]]:
        self.eval()
        with torch.no_grad():
            user_emb = self.user_embeddings(torch.tensor([user_id], dtype=torch.long))
            all_track_embs = self.track_embeddings.weight

            scores = torch.matmul(user_emb, all_track_embs.T).squeeze()

            user_b = self.user_bias(torch.tensor([user_id], dtype=torch.long)).squeeze()
            track_b = self.track_bias.weight.squeeze()
            scores = scores + user_b + track_b + self.global_bias

            if exclude_tracks:
                scores[exclude_tracks] = float('-inf')

            top_k_scores, top_k_indices = torch.topk(scores, k)

            recommendations = [
                (idx.item(), score.item())
                for idx, score in zip(top_k_indices, top_k_scores)
            ]

            return recommendations

    def save(self, path: str):
        torch.save({
            'state_dict': self.state_dict(),
            'num_users': self.num_users,
            'num_tracks': self.num_tracks,
            'embedding_dim': self.embedding_dim,
        }, path)

    @classmethod
    def load(cls, path: str, device='cpu'):
        checkpoint = torch.load(path, map_location=device)
        model = cls(
            num_users=checkpoint['num_users'],
            num_tracks=checkpoint['num_tracks'],
            embedding_dim=checkpoint['embedding_dim']
        )
        model.load_state_dict(checkpoint['state_dict'])
        return model


class ALSCollaborativeFilter:
    def __init__(self, factors: int = 64, regularization: float = 0.01, iterations: int = 15):
        self.factors = factors
        self.regularization = regularization
        self.iterations = iterations
        self.user_factors = None
        self.item_factors = None
        self.user_id_map = {}
        self.track_id_map = {}

    def fit(self, interactions: List[Dict]):
        user_ids = list(set([i['user_id'] for i in interactions]))
        track_ids = list(set([i['track_id'] for i in interactions]))

        self.user_id_map = {uid: idx for idx, uid in enumerate(user_ids)}
        self.track_id_map = {tid: idx for idx, tid in enumerate(track_ids)}

        rows = [self.user_id_map[i['user_id']] for i in interactions]
        cols = [self.track_id_map[i['track_id']] for i in interactions]
        data = [i.get('weight', 1.0) for i in interactions]

        interaction_matrix = csr_matrix(
            (data, (rows, cols)),
            shape=(len(user_ids), len(track_ids))
        )

        svd = TruncatedSVD(n_components=self.factors, random_state=42)
        self.user_factors = svd.fit_transform(interaction_matrix)
        self.item_factors = svd.components_.T

        return self

    def recommend(self, user_id: UUID, k: int = 20) -> List[Tuple[UUID, float]]:
        if user_id not in self.user_id_map:
            return []

        user_idx = self.user_id_map[user_id]
        user_vector = self.user_factors[user_idx]

        scores = np.dot(self.item_factors, user_vector)

        top_k_indices = np.argsort(scores)[::-1][:k]

        reverse_track_map = {idx: tid for tid, idx in self.track_id_map.items()}
        recommendations = [
            (reverse_track_map[idx], scores[idx])
            for idx in top_k_indices
        ]

        return recommendations

    def save(self, path: str):
        with open(path, 'wb') as f:
            pickle.dump({
                'user_factors': self.user_factors,
                'item_factors': self.item_factors,
                'user_id_map': self.user_id_map,
                'track_id_map': self.track_id_map,
                'factors': self.factors,
            }, f)

    @classmethod
    def load(cls, path: str):
        with open(path, 'rb') as f:
            data = pickle.load(f)

        model = cls(factors=data['factors'])
        model.user_factors = data['user_factors']
        model.item_factors = data['item_factors']
        model.user_id_map = data['user_id_map']
        model.track_id_map = data['track_id_map']

        return model