import torch
import torch.nn as nn
from typing import List, Tuple
import numpy as np


class DeepContentModel(nn.Module):
    def __init__(
        self,
        input_dim: int = 512,
        hidden_dims: List[int] = [512, 256, 128],
        output_dim: int = 128,
        dropout: float = 0.3
    ):
        super().__init__()
        self.input_dim = input_dim
        self.output_dim = output_dim

        layers = []
        prev_dim = input_dim

        for hidden_dim in hidden_dims:
            layers.extend([
                nn.Linear(prev_dim, hidden_dim),
                nn.ReLU(),
                nn.BatchNorm1d(hidden_dim),
                nn.Dropout(dropout)
            ])
            prev_dim = hidden_dim

        layers.append(nn.Linear(prev_dim, output_dim))
        layers.append(nn.Tanh())

        self.encoder = nn.Sequential(*layers)

        self._init_weights()

    def _init_weights(self):
        for module in self.modules():
            if isinstance(module, nn.Linear):
                nn.init.xavier_uniform_(module.weight)
                if module.bias is not None:
                    nn.init.zeros_(module.bias)

    def forward(self, audio_features: torch.Tensor) -> torch.Tensor:
        return self.encoder(audio_features)

    def encode(self, audio_features: np.ndarray) -> np.ndarray:
        self.eval()
        with torch.no_grad():
            if audio_features.ndim == 1:
                audio_features = audio_features.reshape(1, -1)

            features_tensor = torch.tensor(audio_features, dtype=torch.float32)
            embeddings = self.forward(features_tensor)

            return embeddings.cpu().numpy()

    def compute_similarity(
        self,
        query_embedding: np.ndarray,
        candidate_embeddings: np.ndarray
    ) -> np.ndarray:
        query_norm = query_embedding / (np.linalg.norm(query_embedding) + 1e-8)

        if candidate_embeddings.ndim == 1:
            candidate_embeddings = candidate_embeddings.reshape(1, -1)

        candidate_norms = candidate_embeddings / (np.linalg.norm(candidate_embeddings, axis=1, keepdims=True) + 1e-8)

        similarities = np.dot(candidate_norms, query_norm)

        return similarities

    def save(self, path: str):
        torch.save({
            'state_dict': self.state_dict(),
            'input_dim': self.input_dim,
            'output_dim': self.output_dim,
        }, path)

    @classmethod
    def load(cls, path: str, device='cpu'):
        checkpoint = torch.load(path, map_location=device)
        model = cls(
            input_dim=checkpoint['input_dim'],
            output_dim=checkpoint['output_dim']
        )
        model.load_state_dict(checkpoint['state_dict'])
        model.to(device)
        return model