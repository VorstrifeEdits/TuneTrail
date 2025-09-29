import os
import torch
import pytorch_lightning as pl
from pytorch_lightning.callbacks import Callback
from typing import Any, Dict, Optional
import logging
from datetime import datetime
import json


class ModelCheckpointCallback(Callback):
    """Enhanced model checkpoint callback with tier-aware saving."""

    def __init__(
        self,
        dirpath: str,
        filename: str = "model-{epoch:02d}-{val_loss:.3f}",
        monitor: str = "val_loss",
        mode: str = "min",
        save_top_k: int = 3,
        save_last: bool = True,
        tier: str = "free"
    ):
        super().__init__()
        self.dirpath = dirpath
        self.filename = filename
        self.monitor = monitor
        self.mode = mode
        self.save_top_k = save_top_k
        self.save_last = save_last
        self.tier = tier

        # Ensure directory exists
        os.makedirs(self.dirpath, exist_ok=True)

        self.logger = logging.getLogger(f"checkpoint.{tier}")

    def on_validation_end(self, trainer: pl.Trainer, pl_module: pl.LightningModule) -> None:
        """Save checkpoint after validation."""
        if trainer.sanity_checking:
            return

        current_epoch = trainer.current_epoch
        metrics = trainer.callback_metrics

        if self.monitor in metrics:
            current_score = float(metrics[self.monitor])

            # Save checkpoint based on criteria
            should_save = self._should_save_checkpoint(current_score, current_epoch)

            if should_save:
                checkpoint_path = self._get_checkpoint_path(current_epoch, current_score)
                self._save_checkpoint(trainer, pl_module, checkpoint_path, metrics)

    def _should_save_checkpoint(self, current_score: float, epoch: int) -> bool:
        """Determine if checkpoint should be saved."""
        # Always save every 10 epochs for backup
        if epoch % 10 == 0:
            return True

        # Save based on monitoring metric
        # Implementation would track best scores
        return True  # Simplified for now

    def _get_checkpoint_path(self, epoch: int, score: float) -> str:
        """Generate checkpoint file path."""
        filename = self.filename.format(epoch=epoch, val_loss=score)
        return os.path.join(self.dirpath, filename)

    def _save_checkpoint(
        self,
        trainer: pl.Trainer,
        pl_module: pl.LightningModule,
        path: str,
        metrics: Dict
    ):
        """Save model checkpoint with metadata."""
        # Save Lightning checkpoint
        trainer.save_checkpoint(path)

        # Save additional metadata
        metadata = {
            'epoch': trainer.current_epoch,
            'global_step': trainer.global_step,
            'metrics': {k: float(v) for k, v in metrics.items() if isinstance(v, torch.Tensor)},
            'tier': self.tier,
            'model_class': pl_module.__class__.__name__,
            'timestamp': datetime.now().isoformat()
        }

        metadata_path = path.replace('.ckpt', '_metadata.json')
        with open(metadata_path, 'w') as f:
            json.dump(metadata, f, indent=2)

        self.logger.info(f"Checkpoint saved: {path}")


class EarlyStoppingCallback(Callback):
    """Enhanced early stopping with tier-specific patience."""

    def __init__(
        self,
        monitor: str = "val_loss",
        patience: int = 7,
        mode: str = "min",
        min_delta: float = 0.0001,
        tier: str = "free"
    ):
        super().__init__()
        self.monitor = monitor
        self.patience = patience
        self.mode = mode
        self.min_delta = min_delta
        self.tier = tier

        self.wait_count = 0
        self.best_score = None
        self.stopped_epoch = 0

        self.logger = logging.getLogger(f"early_stopping.{tier}")

        # Tier-specific patience adjustments
        if tier == "pro":
            self.patience = max(patience, 10)  # More patience for complex models
        elif tier == "starter":
            self.patience = max(patience, 5)

    def on_validation_end(self, trainer: pl.Trainer, pl_module: pl.LightningModule) -> None:
        """Check early stopping criteria."""
        if trainer.sanity_checking:
            return

        metrics = trainer.callback_metrics

        if self.monitor not in metrics:
            self.logger.warning(f"Metric '{self.monitor}' not found in metrics")
            return

        current_score = float(metrics[self.monitor])

        if self._is_improvement(current_score):
            self.best_score = current_score
            self.wait_count = 0
            self.logger.debug(f"New best {self.monitor}: {current_score:.6f}")
        else:
            self.wait_count += 1
            self.logger.debug(
                f"No improvement in {self.monitor}: {current_score:.6f} "
                f"(best: {self.best_score:.6f}, patience: {self.wait_count}/{self.patience})"
            )

            if self.wait_count >= self.patience:
                self.stopped_epoch = trainer.current_epoch
                trainer.should_stop = True
                self.logger.info(
                    f"Early stopping triggered at epoch {self.stopped_epoch} "
                    f"(patience: {self.patience}, best {self.monitor}: {self.best_score:.6f})"
                )

    def _is_improvement(self, score: float) -> bool:
        """Check if current score is an improvement."""
        if self.best_score is None:
            return True

        if self.mode == "min":
            return score < (self.best_score - self.min_delta)
        else:
            return score > (self.best_score + self.min_delta)


class MetricsLoggingCallback(Callback):
    """Enhanced metrics logging with tier-specific insights."""

    def __init__(self, tier: str = "free", log_every_n_epochs: int = 1):
        super().__init__()
        self.tier = tier
        self.log_every_n_epochs = log_every_n_epochs

        self.logger = logging.getLogger(f"metrics.{tier}")
        self.metrics_history = []

    def on_train_epoch_end(self, trainer: pl.Trainer, pl_module: pl.LightningModule) -> None:
        """Log training metrics at epoch end."""
        if trainer.current_epoch % self.log_every_n_epochs != 0:
            return

        metrics = trainer.callback_metrics
        epoch = trainer.current_epoch

        # Extract relevant metrics
        train_metrics = {k: float(v) for k, v in metrics.items() if k.startswith('train_')}
        val_metrics = {k: float(v) for k, v in metrics.items() if k.startswith('val_')}

        # Log epoch summary
        self.logger.info(f"Epoch {epoch} Summary:")
        for name, value in train_metrics.items():
            self.logger.info(f"  {name}: {value:.6f}")
        for name, value in val_metrics.items():
            self.logger.info(f"  {name}: {value:.6f}")

        # Track metrics history
        epoch_metrics = {
            'epoch': epoch,
            'train_metrics': train_metrics,
            'val_metrics': val_metrics,
            'timestamp': datetime.now().isoformat()
        }
        self.metrics_history.append(epoch_metrics)

        # Tier-specific insights
        self._log_tier_specific_insights(epoch, train_metrics, val_metrics)

    def _log_tier_specific_insights(self, epoch: int, train_metrics: Dict, val_metrics: Dict):
        """Log tier-specific training insights."""
        if self.tier == "free":
            # For free tier, focus on convergence speed
            if 'train_loss' in train_metrics and epoch > 5:
                recent_losses = [m['train_metrics'].get('train_loss', 0)
                               for m in self.metrics_history[-5:]]
                if len(recent_losses) == 5:
                    loss_trend = recent_losses[-1] - recent_losses[0]
                    if abs(loss_trend) < 0.001:
                        self.logger.info("📈 Training appears to be converging")

        elif self.tier == "starter":
            # For starter tier, monitor overfitting
            if 'train_loss' in train_metrics and 'val_loss' in val_metrics:
                gap = val_metrics['val_loss'] - train_metrics['train_loss']
                if gap > 0.1:
                    self.logger.warning("⚠️ Potential overfitting detected (val_loss >> train_loss)")

        elif self.tier == "pro":
            # For pro tier, provide detailed analysis
            if 'val_accuracy' in val_metrics:
                accuracy = val_metrics['val_accuracy']
                if accuracy > 0.8:
                    self.logger.info(f"🎯 High accuracy achieved: {accuracy:.3f}")
                elif accuracy < 0.6 and epoch > 10:
                    self.logger.warning(f"⚠️ Low accuracy after 10 epochs: {accuracy:.3f}")

    def on_train_end(self, trainer: pl.Trainer, pl_module: pl.LightningModule) -> None:
        """Log final training summary."""
        total_epochs = trainer.current_epoch

        self.logger.info("🏁 Training Complete!")
        self.logger.info(f"Total epochs: {total_epochs}")

        if self.metrics_history:
            # Find best metrics
            best_train_loss = min(m['train_metrics'].get('train_loss', float('inf'))
                                 for m in self.metrics_history)
            best_val_loss = min(m['val_metrics'].get('val_loss', float('inf'))
                               for m in self.metrics_history)

            self.logger.info(f"Best training loss: {best_train_loss:.6f}")
            self.logger.info(f"Best validation loss: {best_val_loss:.6f}")

            # Save training history
            self._save_training_history()

    def _save_training_history(self):
        """Save complete training history to file."""
        try:
            from config import Config

            history_path = os.path.join(
                Config.MODEL_SAVE_PATH,
                self.tier,
                f"training_history_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            )

            os.makedirs(os.path.dirname(history_path), exist_ok=True)

            with open(history_path, 'w') as f:
                json.dump(self.metrics_history, f, indent=2)

            self.logger.info(f"Training history saved to: {history_path}")

        except Exception as e:
            self.logger.error(f"Failed to save training history: {e}")


class LearningRateMonitorCallback(Callback):
    """Monitor and log learning rate changes."""

    def __init__(self):
        super().__init__()
        self.logger = logging.getLogger("lr_monitor")

    def on_train_epoch_start(self, trainer: pl.Trainer, pl_module: pl.LightningModule) -> None:
        """Log learning rate at epoch start."""
        if hasattr(trainer, 'optimizers'):
            for i, optimizer in enumerate(trainer.optimizers):
                for j, param_group in enumerate(optimizer.param_groups):
                    lr = param_group['lr']
                    self.logger.debug(f"Epoch {trainer.current_epoch} - Optimizer {i}, Group {j}: LR = {lr:.8f}")


class GPUMonitorCallback(Callback):
    """Monitor GPU usage during training."""

    def __init__(self, log_every_n_batches: int = 100):
        super().__init__()
        self.log_every_n_batches = log_every_n_batches
        self.logger = logging.getLogger("gpu_monitor")

    def on_train_batch_end(
        self,
        trainer: pl.Trainer,
        pl_module: pl.LightningModule,
        outputs: Any,
        batch: Any,
        batch_idx: int
    ) -> None:
        """Monitor GPU usage."""
        if batch_idx % self.log_every_n_batches != 0:
            return

        if torch.cuda.is_available():
            try:
                allocated = torch.cuda.memory_allocated() / 1024**3  # GB
                cached = torch.cuda.memory_reserved() / 1024**3  # GB

                self.logger.debug(
                    f"GPU Memory - Allocated: {allocated:.2f}GB, Cached: {cached:.2f}GB"
                )

                # Warn if memory usage is high
                if allocated > 10:  # 10GB threshold
                    self.logger.warning(f"High GPU memory usage: {allocated:.2f}GB")

            except Exception as e:
                self.logger.debug(f"Failed to get GPU memory info: {e}")