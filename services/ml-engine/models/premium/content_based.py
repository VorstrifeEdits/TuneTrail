import numpy as np
from typing import List, Dict, Tuple, Optional
from uuid import UUID
import faiss
from sklearn.metrics.pairwise import cosine_similarity
from collections import defaultdict


class ContentBasedModel:
    def __init__(self, embedding_dim: int = 512, use_gpu: bool = False):
        self.embedding_dim = embedding_dim
        self.use_gpu = use_gpu

        self.track_embeddings = {}
        self.track_features = {}
        self.faiss_index = None
        self.track_id_to_idx = {}
        self.idx_to_track_id = {}

    def fit(self, track_features: List[Dict]):
        embeddings_list = []
        track_ids = []

        for idx, track in enumerate(track_features):
            track_id = track['track_id']
            embedding = track.get('embedding')

            if embedding is None or len(embedding) != self.embedding_dim:
                continue

            self.track_embeddings[track_id] = np.array(embedding, dtype=np.float32)
            self.track_features[track_id] = {
                'tempo': track.get('tempo'),
                'energy': track.get('energy'),
                'valence': track.get('valence'),
                'danceability': track.get('danceability'),
                'acousticness': track.get('acousticness'),
                'genre': track.get('genre'),
            }

            embeddings_list.append(embedding)
            track_ids.append(track_id)
            self.track_id_to_idx[track_id] = idx
            self.idx_to_track_id[idx] = track_id

        if not embeddings_list:
            raise ValueError("No valid embeddings found in track_features")

        embeddings_matrix = np.array(embeddings_list, dtype=np.float32)

        faiss.normalize_L2(embeddings_matrix)

        if self.use_gpu and faiss.get_num_gpus() > 0:
            res = faiss.StandardGpuResources()
            self.faiss_index = faiss.GpuIndexFlatIP(res, self.embedding_dim)
        else:
            self.faiss_index = faiss.IndexFlatIP(self.embedding_dim)

        self.faiss_index.add(embeddings_matrix)

        return self

    def find_similar(
        self,
        track_id: UUID,
        k: int = 20,
        min_similarity: float = 0.7,
        genre_filter: Optional[str] = None
    ) -> List[Tuple[UUID, float]]:
        if track_id not in self.track_embeddings:
            return []

        query_embedding = self.track_embeddings[track_id].reshape(1, -1).astype(np.float32)
        faiss.normalize_L2(query_embedding)

        search_k = k * 5 if genre_filter else k + 1

        distances, indices = self.faiss_index.search(query_embedding, search_k)

        similar_tracks = []
        for dist, idx in zip(distances[0], indices[0]):
            if idx == -1:
                continue

            similar_track_id = self.idx_to_track_id[idx]

            if similar_track_id == track_id:
                continue

            similarity = float(dist)

            if similarity < min_similarity:
                continue

            if genre_filter:
                track_genre = self.track_features.get(similar_track_id, {}).get('genre')
                if track_genre != genre_filter:
                    continue

            similar_tracks.append((similar_track_id, similarity))

            if len(similar_tracks) >= k:
                break

        return similar_tracks

    def recommend_by_features(
        self,
        target_features: Dict,
        k: int = 20,
        exclude_tracks: Optional[List[UUID]] = None
    ) -> List[Tuple[UUID, float]]:
        exclude_set = set(exclude_tracks) if exclude_tracks else set()

        target_tempo = target_features.get('tempo', 120)
        target_energy = target_features.get('energy', 0.5)
        target_valence = target_features.get('valence', 0.5)
        target_danceability = target_features.get('danceability', 0.5)

        track_scores = []
        for track_id, features in self.track_features.items():
            if track_id in exclude_set:
                continue

            if any(features[k] is None for k in ['tempo', 'energy', 'valence', 'danceability']):
                continue

            tempo_diff = abs(features['tempo'] - target_tempo) / 200.0
            energy_diff = abs(features['energy'] - target_energy)
            valence_diff = abs(features['valence'] - target_valence)
            dance_diff = abs(features['danceability'] - target_danceability)

            score = 1.0 - (0.2 * tempo_diff + 0.3 * energy_diff + 0.3 * valence_diff + 0.2 * dance_diff)

            track_scores.append((track_id, max(0.0, score)))

        track_scores.sort(key=lambda x: x[1], reverse=True)

        return track_scores[:k]

    def build_user_taste_profile(self, user_track_history: List[UUID]) -> Dict:
        if not user_track_history:
            return {}

        valid_embeddings = [
            self.track_embeddings[tid]
            for tid in user_track_history
            if tid in self.track_embeddings
        ]

        if not valid_embeddings:
            return {}

        avg_embedding = np.mean(valid_embeddings, axis=0)

        feature_arrays = defaultdict(list)
        for track_id in user_track_history:
            if track_id in self.track_features:
                features = self.track_features[track_id]
                for key, value in features.items():
                    if value is not None and key != 'genre':
                        feature_arrays[key].append(value)

        avg_features = {
            key: np.mean(values) if values else None
            for key, values in feature_arrays.items()
        }

        return {
            'embedding': avg_embedding,
            'features': avg_features,
        }

    def save(self, path: str):
        import pickle

        faiss.write_index(self.faiss_index, f"{path}.faiss")

        with open(f"{path}.pkl", 'wb') as f:
            pickle.dump({
                'track_embeddings': self.track_embeddings,
                'track_features': self.track_features,
                'track_id_to_idx': self.track_id_to_idx,
                'idx_to_track_id': self.idx_to_track_id,
                'embedding_dim': self.embedding_dim,
            }, f)

    @classmethod
    def load(cls, path: str, use_gpu: bool = False):
        import pickle

        with open(f"{path}.pkl", 'rb') as f:
            data = pickle.load(f)

        model = cls(embedding_dim=data['embedding_dim'], use_gpu=use_gpu)
        model.track_embeddings = data['track_embeddings']
        model.track_features = data['track_features']
        model.track_id_to_idx = data['track_id_to_idx']
        model.idx_to_track_id = data['idx_to_track_id']

        model.faiss_index = faiss.read_index(f"{path}.faiss")

        if use_gpu and faiss.get_num_gpus() > 0:
            res = faiss.StandardGpuResources()
            model.faiss_index = faiss.index_cpu_to_gpu(res, 0, model.faiss_index)

        return model