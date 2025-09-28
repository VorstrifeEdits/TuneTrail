import torch
import torch.nn as nn
from typing import List, Tuple
import numpy as np


class DeepHybridModel(nn.Module):
    def __init__(
        self,
        num_users: int,
        num_tracks: int,
        audio_feature_dim: int = 512,
        user_emb_dim: int = 128,
        track_emb_dim: int = 128,
        hidden_dims: List[int] = [512, 256, 128],
        dropout: float = 0.2
    ):
        super().__init__()
        self.num_users = num_users
        self.num_tracks = num_tracks

        self.user_embedding = nn.Embedding(num_users, user_emb_dim)
        self.track_embedding = nn.Embedding(num_tracks, track_emb_dim)

        self.audio_encoder = nn.Sequential(
            nn.Linear(audio_feature_dim, 256),
            nn.ReLU(),
            nn.BatchNorm1d(256),
            nn.Dropout(dropout),
            nn.Linear(256, track_emb_dim),
            nn.ReLU()
        )

        combined_dim = user_emb_dim + track_emb_dim * 2

        fusion_layers = []
        prev_dim = combined_dim

        for hidden_dim in hidden_dims:
            fusion_layers.extend([
                nn.Linear(prev_dim, hidden_dim),
                nn.ReLU(),
                nn.BatchNorm1d(hidden_dim),
                nn.Dropout(dropout)
            ])
            prev_dim = hidden_dim

        fusion_layers.append(nn.Linear(prev_dim, 1))
        fusion_layers.append(nn.Sigmoid())

        self.fusion_network = nn.Sequential(*fusion_layers)

        self._init_weights()

    def _init_weights(self):
        nn.init.normal_(self.user_embedding.weight, std=0.01)
        nn.init.normal_(self.track_embedding.weight, std=0.01)

        for module in self.modules():
            if isinstance(module, nn.Linear):
                nn.init.xavier_uniform_(module.weight)
                if module.bias is not None:
                    nn.init.zeros_(module.bias)

    def forward(
        self,
        user_ids: torch.Tensor,
        track_ids: torch.Tensor,
        audio_features: torch.Tensor
    ) -> torch.Tensor:
        user_emb = self.user_embedding(user_ids)
        track_emb = self.track_embedding(track_ids)

        audio_emb = self.audio_encoder(audio_features)

        combined = torch.cat([user_emb, track_emb, audio_emb], dim=-1)

        prediction = self.fusion_network(combined)

        return prediction.squeeze()

    def predict(
        self,
        user_id: int,
        track_ids: List[int],
        audio_features_list: List[np.ndarray]
    ) -> np.ndarray:
        self.eval()
        with torch.no_grad():
            user_tensor = torch.tensor([user_id] * len(track_ids), dtype=torch.long)
            track_tensor = torch.tensor(track_ids, dtype=torch.long)
            audio_tensor = torch.tensor(audio_features_list, dtype=torch.float32)

            scores = self.forward(user_tensor, track_tensor, audio_tensor)

            return scores.cpu().numpy()

    def save(self, path: str):
        torch.save({
            'state_dict': self.state_dict(),
            'num_users': self.num_users,
            'num_tracks': self.num_tracks,
        }, path)

    @classmethod
    def load(cls, path: str, device='cpu'):
        checkpoint = torch.load(path, map_location=device)
        model = cls(
            num_users=checkpoint['num_users'],
            num_tracks=checkpoint['num_tracks']
        )
        model.load_state_dict(checkpoint['state_dict'])
        model.to(device)
        return model