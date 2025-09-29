import os
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, Dataset
import pytorch_lightning as pl
from typing import Dict, List, Optional, Tuple, Any
from uuid import UUID
from abc import ABC, abstractmethod
import logging
from datetime import datetime

from config import Config
from utils.metrics import compute_recall_at_k, compute_ndcg, compute_mrr


class BaseTrainer(ABC):
    """Base trainer class for all recommendation models."""

    def __init__(self, model_name: str, config: Dict = None):
        self.model_name = model_name
        self.config = config or {}
        self.logger = logging.getLogger(f"trainer.{model_name}")
        self.device = torch.device('cuda' if Config.ENABLE_GPU and torch.cuda.is_available() else 'cpu')

    @abstractmethod
    def train(self, train_data: Any, val_data: Any = None) -> Dict:
        """Train the model and return metrics."""
        pass

    @abstractmethod
    def save_model(self, path: str):
        """Save the trained model."""
        pass

    def log_metrics(self, metrics: Dict, step: int = None):
        """Log training metrics."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.logger.info(f"[{timestamp}] Step {step} - Metrics: {metrics}")


class InteractionDataset(Dataset):
    """Dataset for user-track interactions."""

    def __init__(self, interactions: List[Dict], user_map: Dict, track_map: Dict):
        self.interactions = interactions
        self.user_map = user_map
        self.track_map = track_map

        # Filter interactions that have valid mappings
        self.valid_interactions = []
        for interaction in interactions:
            user_id = interaction['user_id']
            track_id = interaction['track_id']
            if user_id in user_map and track_id in track_map:
                self.valid_interactions.append({
                    'user_idx': user_map[user_id],
                    'track_idx': track_map[track_id],
                    'rating': 1.0 if interaction['interaction_type'] == 'like' else 0.5,
                    'interaction_type': interaction['interaction_type']
                })

    def __len__(self):
        return len(self.valid_interactions)

    def __getitem__(self, idx):
        interaction = self.valid_interactions[idx]
        return {
            'user_idx': torch.tensor(interaction['user_idx'], dtype=torch.long),
            'track_idx': torch.tensor(interaction['track_idx'], dtype=torch.long),
            'rating': torch.tensor(interaction['rating'], dtype=torch.float32)
        }


class CollaborativeFilterTrainer(BaseTrainer):
    """Trainer for collaborative filtering models (ALS and Neural CF)."""

    def __init__(self, config: Dict = None):
        super().__init__("collaborative_filter", config)

    def prepare_data(self, interactions: List[Dict]) -> Tuple[Dict, Dict, InteractionDataset, InteractionDataset]:
        """Prepare interaction data for training."""
        # Create user and track mappings
        unique_users = list(set(i['user_id'] for i in interactions))
        unique_tracks = list(set(i['track_id'] for i in interactions))

        user_map = {uid: idx for idx, uid in enumerate(unique_users)}
        track_map = {tid: idx for idx, tid in enumerate(unique_tracks)}

        # Split data into train/validation (80/20)
        split_idx = int(len(interactions) * 0.8)
        train_interactions = interactions[:split_idx]
        val_interactions = interactions[split_idx:]

        train_dataset = InteractionDataset(train_interactions, user_map, track_map)
        val_dataset = InteractionDataset(val_interactions, user_map, track_map)

        self.logger.info(f"Data prepared: {len(unique_users)} users, {len(unique_tracks)} tracks")
        self.logger.info(f"Train: {len(train_dataset)} interactions, Val: {len(val_dataset)} interactions")

        return user_map, track_map, train_dataset, val_dataset

    def train_als_model(self, interactions: List[Dict]) -> Dict:
        """Train ALS collaborative filtering model."""
        from models.base.collaborative_filter import ALSCollaborativeFilter

        self.logger.info("Training ALS Collaborative Filter...")

        model = ALSCollaborativeFilter(
            factors=self.config.get('embedding_dim', 64),
            regularization=self.config.get('regularization', 0.01),
            iterations=self.config.get('iterations', 15)
        )

        # Train the model
        model.fit(interactions)

        # Save model
        model_path = os.path.join(Config.MODEL_SAVE_PATH, "free", "collaborative_filter_als.pkl")
        os.makedirs(os.path.dirname(model_path), exist_ok=True)
        model.save(model_path)

        # Evaluate model (simple validation)
        num_users = len(set(i['user_id'] for i in interactions))
        metrics = {
            'model_type': 'ALS',
            'num_users': num_users,
            'num_interactions': len(interactions),
            'factors': model.factors,
            'training_time': 'completed'
        }

        self.log_metrics(metrics)
        return metrics

    def train(self, train_data: List[Dict], val_data: List[Dict] = None) -> Dict:
        """Train collaborative filtering model."""
        return self.train_als_model(train_data)

    def save_model(self, path: str):
        """ALS model is saved during training."""
        pass


class NeuralCFLightningModule(pl.LightningModule):
    """PyTorch Lightning module for Neural Collaborative Filtering."""

    def __init__(self, num_users: int, num_tracks: int, config: Dict):
        super().__init__()
        self.save_hyperparameters()

        from models.enterprise.neural_cf import NeuralCF
        self.model = NeuralCF(
            num_users=num_users,
            num_tracks=num_tracks,
            emb_dim=config.get('embedding_dim', 128),
            hidden_dims=config.get('hidden_dims', [256, 128, 64]),
            dropout=config.get('dropout', 0.2)
        )

        self.lr = config.get('learning_rate', 0.001)
        self.criterion = nn.BCELoss()

    def forward(self, user_ids, track_ids):
        return self.model(user_ids, track_ids)

    def training_step(self, batch, batch_idx):
        user_ids = batch['user_idx']
        track_ids = batch['track_idx']
        ratings = batch['rating']

        # Neural CF expects binary targets
        targets = (ratings > 0.5).float()

        predictions = self.forward(user_ids, track_ids)
        loss = self.criterion(predictions, targets)

        self.log('train_loss', loss, on_step=True, on_epoch=True, prog_bar=True)
        return loss

    def validation_step(self, batch, batch_idx):
        user_ids = batch['user_idx']
        track_ids = batch['track_idx']
        ratings = batch['rating']

        targets = (ratings > 0.5).float()
        predictions = self.forward(user_ids, track_ids)
        loss = self.criterion(predictions, targets)

        # Calculate accuracy
        pred_binary = (predictions > 0.5).float()
        accuracy = (pred_binary == targets).float().mean()

        self.log('val_loss', loss, on_epoch=True, prog_bar=True)
        self.log('val_accuracy', accuracy, on_epoch=True, prog_bar=True)

        return {'val_loss': loss, 'val_accuracy': accuracy}

    def configure_optimizers(self):
        optimizer = torch.optim.Adam(self.parameters(), lr=self.lr)
        scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(
            optimizer, mode='min', factor=0.5, patience=5, verbose=True
        )
        return {
            'optimizer': optimizer,
            'lr_scheduler': {
                'scheduler': scheduler,
                'monitor': 'val_loss',
            }
        }


class NeuralCFTrainer(BaseTrainer):
    """Trainer for Neural Collaborative Filtering using PyTorch Lightning."""

    def __init__(self, config: Dict = None):
        super().__init__("neural_cf", config)

    def train(self, train_data: List[Dict], val_data: List[Dict] = None) -> Dict:
        """Train Neural CF model using PyTorch Lightning."""
        self.logger.info("Training Neural Collaborative Filtering...")

        # Prepare data
        cf_trainer = CollaborativeFilterTrainer()
        user_map, track_map, train_dataset, val_dataset = cf_trainer.prepare_data(train_data)

        # Create data loaders
        train_loader = DataLoader(
            train_dataset,
            batch_size=self.config.get('batch_size', 512),
            shuffle=True,
            num_workers=4,
            pin_memory=True
        )

        val_loader = DataLoader(
            val_dataset,
            batch_size=self.config.get('batch_size', 512),
            shuffle=False,
            num_workers=4,
            pin_memory=True
        )

        # Initialize Lightning module
        lightning_model = NeuralCFLightningModule(
            num_users=len(user_map),
            num_tracks=len(track_map),
            config=self.config
        )

        # Configure trainer
        trainer = pl.Trainer(
            max_epochs=self.config.get('epochs', 50),
            accelerator='gpu' if Config.ENABLE_GPU else 'cpu',
            devices=1,
            enable_progress_bar=True,
            enable_model_summary=True,
            callbacks=[
                pl.callbacks.EarlyStopping(
                    monitor='val_loss',
                    patience=self.config.get('early_stopping_patience', 5),
                    mode='min'
                ),
                pl.callbacks.ModelCheckpoint(
                    dirpath=os.path.join(Config.MODEL_SAVE_PATH, "pro"),
                    filename='neural_cf-{epoch:02d}-{val_loss:.3f}',
                    monitor='val_loss',
                    mode='min',
                    save_top_k=1
                )
            ],
            logger=pl.loggers.TensorBoardLogger(
                save_dir=os.path.join(Config.MODEL_SAVE_PATH, "logs"),
                name="neural_cf"
            )
        )

        # Train model
        trainer.fit(lightning_model, train_loader, val_loader)

        # Save the final model
        self.save_model(lightning_model, user_map, track_map)

        # Prepare metrics
        metrics = {
            'model_type': 'Neural CF',
            'num_users': len(user_map),
            'num_tracks': len(track_map),
            'num_epochs': trainer.current_epoch,
            'best_val_loss': float(trainer.checkpoint_callback.best_model_score),
            'training_time': 'completed'
        }

        self.log_metrics(metrics)
        return metrics

    def save_model(self, lightning_model: NeuralCFLightningModule, user_map: Dict, track_map: Dict):
        """Save the trained Neural CF model."""
        model_path = os.path.join(Config.MODEL_SAVE_PATH, "pro", "neural_cf.pt")
        os.makedirs(os.path.dirname(model_path), exist_ok=True)

        # Save the PyTorch model (not Lightning module)
        neural_cf_model = lightning_model.model
        neural_cf_model.save(model_path)

        # Save mappings
        mappings_path = os.path.join(Config.MODEL_SAVE_PATH, "pro", "neural_cf_mappings.pkl")
        import pickle
        with open(mappings_path, 'wb') as f:
            pickle.dump({
                'user_map': user_map,
                'track_map': track_map
            }, f)

        self.logger.info(f"Neural CF model saved to {model_path}")


class PopularityTrainer(BaseTrainer):
    """Trainer for popularity-based recommendation model."""

    def __init__(self, config: Dict = None):
        super().__init__("popularity", config)

    def train(self, train_data: List[Dict], val_data: List[Dict] = None) -> Dict:
        """Train popularity model."""
        from models.base.popularity import PopularityModel

        self.logger.info("Training Popularity Model...")

        model = PopularityModel(
            time_decay_days=self.config.get('time_decay_days', 30),
            min_plays=self.config.get('min_plays', 5)
        )

        # Train the model
        model.fit(train_data)

        # Save model
        model_path = os.path.join(Config.MODEL_SAVE_PATH, "free", "popularity.pkl")
        os.makedirs(os.path.dirname(model_path), exist_ok=True)
        model.save(model_path)

        # Calculate metrics
        metrics = {
            'model_type': 'Popularity',
            'num_interactions': len(train_data),
            'time_decay_days': model.time_decay_days,
            'min_plays': model.min_plays,
            'num_tracks_with_scores': len(model.track_scores),
            'training_time': 'completed'
        }

        self.log_metrics(metrics)
        return metrics

    def save_model(self, path: str):
        """Popularity model is saved during training."""
        pass


class GenreBasedTrainer(BaseTrainer):
    """Trainer for genre-based recommendation model."""

    def __init__(self, config: Dict = None):
        super().__init__("genre_based", config)

    def train(self, interactions: List[Dict], tracks: Dict, val_data: List[Dict] = None) -> Dict:
        """Train genre-based model."""
        from models.base.genre_based import GenreBasedModel

        self.logger.info("Training Genre-Based Model...")

        model = GenreBasedModel()

        # Convert tracks dict to list format
        tracks_list = list(tracks.values())

        # Train the model
        model.fit(interactions, tracks_list)

        # Save model
        model_path = os.path.join(Config.MODEL_SAVE_PATH, "free", "genre_based.pkl")
        os.makedirs(os.path.dirname(model_path), exist_ok=True)
        model.save(model_path)

        # Calculate metrics
        metrics = {
            'model_type': 'Genre-Based',
            'num_interactions': len(interactions),
            'num_tracks': len(tracks_list),
            'num_genres': len(model.genre_tracks),
            'num_users_with_preferences': len(model.user_genre_preferences),
            'training_time': 'completed'
        }

        self.log_metrics(metrics)
        return metrics

    def save_model(self, path: str):
        """Genre-based model is saved during training."""
        pass


class ContentBasedTrainer(BaseTrainer):
    """Trainer for content-based recommendation model."""

    def __init__(self, config: Dict = None):
        super().__init__("content_based", config)

    def train(self, audio_features: List[Dict], val_data: List[Dict] = None) -> Dict:
        """Train content-based model."""
        from models.premium.content_based import ContentBasedModel

        self.logger.info("Training Content-Based Model...")

        model = ContentBasedModel(
            embedding_dim=self.config.get('embedding_dim', 512),
            use_gpu=Config.ENABLE_GPU
        )

        # Train the model (builds FAISS index)
        model.fit(audio_features)

        # Save model
        model_path = os.path.join(Config.MODEL_SAVE_PATH, "starter", "content_based")
        os.makedirs(os.path.dirname(model_path), exist_ok=True)
        model.save(model_path)

        # Calculate metrics
        metrics = {
            'model_type': 'Content-Based',
            'num_tracks_with_features': len(audio_features),
            'embedding_dim': model.embedding_dim,
            'faiss_index_size': model.faiss_index.ntotal if model.faiss_index else 0,
            'use_gpu': model.use_gpu,
            'training_time': 'completed'
        }

        self.log_metrics(metrics)
        return metrics

    def save_model(self, path: str):
        """Content-based model is saved during training."""
        pass