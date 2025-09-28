import torch
import torch.nn as nn
import torch.nn.functional as F
from typing import List, Tuple
from uuid import UUID
import numpy as np


class NeuralCF(nn.Module):
    def __init__(
        self,
        num_users: int,
        num_tracks: int,
        emb_dim: int = 128,
        hidden_dims: List[int] = [256, 128, 64],
        dropout: float = 0.2
    ):
        super().__init__()
        self.num_users = num_users
        self.num_tracks = num_tracks
        self.emb_dim = emb_dim

        self.user_embedding = nn.Embedding(num_users, emb_dim)
        self.track_embedding = nn.Embedding(num_tracks, emb_dim)

        self.user_mf_embedding = nn.Embedding(num_users, emb_dim)
        self.track_mf_embedding = nn.Embedding(num_tracks, emb_dim)

        mlp_layers = []
        input_dim = emb_dim * 2

        for hidden_dim in hidden_dims:
            mlp_layers.extend([
                nn.Linear(input_dim, hidden_dim),
                nn.ReLU(),
                nn.BatchNorm1d(hidden_dim),
                nn.Dropout(dropout)
            ])
            input_dim = hidden_dim

        self.mlp = nn.Sequential(*mlp_layers)

        self.predict_layer = nn.Linear(hidden_dims[-1] + emb_dim, 1)

        self._init_weights()

    def _init_weights(self):
        nn.init.normal_(self.user_embedding.weight, std=0.01)
        nn.init.normal_(self.track_embedding.weight, std=0.01)
        nn.init.normal_(self.user_mf_embedding.weight, std=0.01)
        nn.init.normal_(self.track_mf_embedding.weight, std=0.01)

        for layer in self.mlp:
            if isinstance(layer, nn.Linear):
                nn.init.xavier_uniform_(layer.weight)
                nn.init.zeros_(layer.bias)

        nn.init.xavier_uniform_(self.predict_layer.weight)
        nn.init.zeros_(self.predict_layer.bias)

    def forward(self, user_ids: torch.Tensor, track_ids: torch.Tensor) -> torch.Tensor:
        user_emb_mlp = self.user_embedding(user_ids)
        track_emb_mlp = self.track_embedding(track_ids)

        mlp_input = torch.cat([user_emb_mlp, track_emb_mlp], dim=-1)
        mlp_output = self.mlp(mlp_input)

        user_emb_mf = self.user_mf_embedding(user_ids)
        track_emb_mf = self.track_mf_embedding(track_ids)
        mf_output = user_emb_mf * track_emb_mf

        combined = torch.cat([mlp_output, mf_output], dim=-1)
        prediction = self.predict_layer(combined)

        return torch.sigmoid(prediction).squeeze()

    def predict(self, user_id: int, track_ids: List[int]) -> np.ndarray:
        self.eval()
        with torch.no_grad():
            user_tensor = torch.tensor([user_id] * len(track_ids), dtype=torch.long)
            track_tensor = torch.tensor(track_ids, dtype=torch.long)
            scores = self.forward(user_tensor, track_tensor)
            return scores.cpu().numpy()

    def recommend(
        self,
        user_id: int,
        k: int = 20,
        exclude_tracks: List[int] = None,
        candidate_tracks: List[int] = None
    ) -> List[Tuple[int, float]]:
        self.eval()
        with torch.no_grad():
            if candidate_tracks is None:
                candidate_tracks = list(range(self.num_tracks))

            if exclude_tracks:
                exclude_set = set(exclude_tracks)
                candidate_tracks = [t for t in candidate_tracks if t not in exclude_set]

            if len(candidate_tracks) == 0:
                return []

            batch_size = 1024
            all_scores = []

            for i in range(0, len(candidate_tracks), batch_size):
                batch_tracks = candidate_tracks[i:i+batch_size]
                user_tensor = torch.tensor([user_id] * len(batch_tracks), dtype=torch.long)
                track_tensor = torch.tensor(batch_tracks, dtype=torch.long)

                batch_scores = self.forward(user_tensor, track_tensor)
                all_scores.extend(zip(batch_tracks, batch_scores.cpu().numpy()))

            all_scores.sort(key=lambda x: x[1], reverse=True)

            return all_scores[:k]

    def get_user_embedding(self, user_id: int) -> np.ndarray:
        self.eval()
        with torch.no_grad():
            user_tensor = torch.tensor([user_id], dtype=torch.long)
            emb = self.user_embedding(user_tensor)
            return emb.cpu().numpy()[0]

    def get_track_embedding(self, track_id: int) -> np.ndarray:
        self.eval()
        with torch.no_grad():
            track_tensor = torch.tensor([track_id], dtype=torch.long)
            emb = self.track_embedding(track_tensor)
            return emb.cpu().numpy()[0]

    def save(self, path: str):
        torch.save({
            'state_dict': self.state_dict(),
            'num_users': self.num_users,
            'num_tracks': self.num_tracks,
            'emb_dim': self.emb_dim,
            'hidden_dims': [256, 128, 64],
        }, path)

    @classmethod
    def load(cls, path: str, device='cpu'):
        checkpoint = torch.load(path, map_location=device)
        model = cls(
            num_users=checkpoint['num_users'],
            num_tracks=checkpoint['num_tracks'],
            emb_dim=checkpoint['emb_dim'],
            hidden_dims=checkpoint.get('hidden_dims', [256, 128, 64])
        )
        model.load_state_dict(checkpoint['state_dict'])
        model.to(device)
        return model