from enum import Enum
from pydantic import BaseModel
from typing import Optional
import os


class ModelTier(str, Enum):
    FREE = "free"
    STARTER = "starter"
    PRO = "pro"
    ENTERPRISE = "enterprise"


class ModelConfig(BaseModel):
    embedding_dim: int = 128
    hidden_dims: list[int] = [256, 128, 64]
    dropout: float = 0.2
    learning_rate: float = 0.001
    batch_size: int = 512
    epochs: int = 50
    early_stopping_patience: int = 5


class Config:
    DATABASE_URL = os.getenv("DATABASE_URL")
    REDIS_URL = os.getenv("REDIS_URL")
    MODEL_TIER = os.getenv("MODEL_TIER", "basic")
    ENABLE_GPU = os.getenv("ENABLE_GPU", "false").lower() == "true"

    MODEL_SAVE_PATH = "/models"
    FAISS_INDEX_PATH = "/models/faiss_indexes"

    FREE_MODELS = {
        "collaborative_filter": ModelConfig(embedding_dim=64),
        "popularity": ModelConfig(),
        "genre_based": ModelConfig(),
    }

    STARTER_MODELS = {
        "content_based": ModelConfig(embedding_dim=512),
        "hybrid_simple": ModelConfig(embedding_dim=128),
        "daily_mix": ModelConfig(),
    }

    PRO_MODELS = {
        "neural_cf": ModelConfig(embedding_dim=128, hidden_dims=[256, 128, 64]),
        "deep_content": ModelConfig(embedding_dim=512, hidden_dims=[512, 256, 128]),
        "hybrid_deep": ModelConfig(embedding_dim=256, hidden_dims=[512, 256, 128]),
        "taste_profiler": ModelConfig(),
    }

    ENTERPRISE_MODELS = {
        "custom_trainer": ModelConfig(embedding_dim=256),
    }

    RECOMMENDATION_CACHE_TTL = 3600
    SIMILARITY_CACHE_TTL = 86400

    FAISS_NLIST = 100
    FAISS_NPROBE = 10

    TRAINING_SCHEDULE = {
        "free": "0 4 * * *",
        "starter": "0 5 * * *",
        "pro": "0 7 * * *",
        "enterprise": "0 10 * * *",
    }