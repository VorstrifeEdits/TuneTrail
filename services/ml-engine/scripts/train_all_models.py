#!/usr/bin/env python3
"""
TuneTrail ML Engine - Complete Model Training Pipeline

This script trains all recommendation models across all tiers:
- Free Tier: Collaborative Filtering (ALS), Popularity, Genre-Based
- Starter Tier: Content-Based (FAISS), Daily Mix Generator
- Pro Tier: Neural Collaborative Filtering, Taste Profiler

Usage:
    python scripts/train_all_models.py [--tier free|starter|pro|all] [--force] [--evaluate]

Examples:
    python scripts/train_all_models.py --tier all --evaluate
    python scripts/train_all_models.py --tier free --force
    python scripts/train_all_models.py --tier pro
"""

import asyncio
import argparse
import sys
import os
import logging
from datetime import datetime
from typing import Dict, List

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import Config
from data.loaders import load_training_data, load_tracks, load_audio_features
from training.trainers import (
    CollaborativeFilterTrainer,
    PopularityTrainer,
    GenreBasedTrainer,
    ContentBasedTrainer,
    NeuralCFTrainer
)
from training.evaluators import ModelEvaluator


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('/models/training.log')
    ]
)

logger = logging.getLogger("train_all_models")


class TrainingPipeline:
    """Complete training pipeline for all ML models."""

    def __init__(self, force_retrain: bool = False):
        self.force_retrain = force_retrain
        self.training_results = {}
        self.start_time = datetime.now()

    async def run_complete_training(self, tiers: List[str] = None, evaluate: bool = False) -> Dict:
        """
        Run the complete training pipeline.

        Args:
            tiers: List of tiers to train ['free', 'starter', 'pro'] or None for all
            evaluate: Whether to run evaluation after training

        Returns:
            Dictionary with training results and metrics
        """
        if tiers is None:
            tiers = ['free', 'starter', 'pro']

        logger.info("=" * 60)
        logger.info("🚀 Starting TuneTrail ML Training Pipeline")
        logger.info("=" * 60)
        logger.info(f"Training tiers: {', '.join(tiers)}")
        logger.info(f"Force retrain: {self.force_retrain}")
        logger.info(f"Evaluate after training: {evaluate}")
        logger.info(f"GPU enabled: {Config.ENABLE_GPU}")

        try:
            # Load all required data upfront
            await self._load_training_data()

            # Train models by tier
            if 'free' in tiers:
                await self._train_free_tier()

            if 'starter' in tiers:
                await self._train_starter_tier()

            if 'pro' in tiers:
                await self._train_pro_tier()

            # Run evaluation if requested
            if evaluate:
                await self._run_evaluation()

            # Generate final report
            self._generate_final_report()

            return self.training_results

        except Exception as e:
            logger.error(f"Training pipeline failed: {e}")
            raise

    async def _load_training_data(self):
        """Load and prepare all training data."""
        logger.info("📊 Loading training data...")

        # Load interaction data
        self.train_data, self.val_data = await load_training_data(train_ratio=0.8)
        logger.info(f"Loaded {len(self.train_data)} training interactions")
        logger.info(f"Loaded {len(self.val_data)} validation interactions")

        if not self.train_data:
            raise ValueError("No training data available! Please ensure interactions exist in the database.")

        # Load tracks data
        self.tracks = await load_tracks()
        logger.info(f"Loaded {len(self.tracks)} tracks")

        # Load audio features
        self.audio_features = await load_audio_features()
        logger.info(f"Loaded {len(self.audio_features)} tracks with audio features")

        if not self.audio_features:
            logger.warning("No audio features found! Content-based models will be skipped.")

        # Data quality checks
        unique_users = len(set(i['user_id'] for i in self.train_data))
        unique_tracks = len(set(i['track_id'] for i in self.train_data))

        logger.info(f"Data quality: {unique_users} unique users, {unique_tracks} unique tracks")

        if unique_users < 10:
            logger.warning("Very few users in dataset. Model quality may be poor.")

        if unique_tracks < 100:
            logger.warning("Very few tracks in dataset. Model quality may be poor.")

    async def _train_free_tier(self):
        """Train all Free Tier models."""
        logger.info("\n🆓 Training Free Tier Models")
        logger.info("-" * 40)

        free_results = {}

        # 1. Collaborative Filtering (ALS)
        try:
            logger.info("Training Collaborative Filtering (ALS)...")
            cf_trainer = CollaborativeFilterTrainer(Config.FREE_MODELS.get('collaborative_filter', {}))
            cf_results = cf_trainer.train(self.train_data, self.val_data)
            free_results['collaborative_filter'] = cf_results
            logger.info("✅ Collaborative Filtering training completed")
        except Exception as e:
            logger.error(f"❌ Collaborative Filtering training failed: {e}")
            free_results['collaborative_filter'] = {'error': str(e)}

        # 2. Popularity Model
        try:
            logger.info("Training Popularity Model...")
            pop_trainer = PopularityTrainer(Config.FREE_MODELS.get('popularity', {}))
            pop_results = pop_trainer.train(self.train_data, self.val_data)
            free_results['popularity'] = pop_results
            logger.info("✅ Popularity Model training completed")
        except Exception as e:
            logger.error(f"❌ Popularity Model training failed: {e}")
            free_results['popularity'] = {'error': str(e)}

        # 3. Genre-Based Model
        try:
            logger.info("Training Genre-Based Model...")
            genre_trainer = GenreBasedTrainer(Config.FREE_MODELS.get('genre_based', {}))
            genre_results = genre_trainer.train(self.train_data, self.tracks, self.val_data)
            free_results['genre_based'] = genre_results
            logger.info("✅ Genre-Based Model training completed")
        except Exception as e:
            logger.error(f"❌ Genre-Based Model training failed: {e}")
            free_results['genre_based'] = {'error': str(e)}

        self.training_results['free_tier'] = free_results

    async def _train_starter_tier(self):
        """Train all Starter Tier models."""
        logger.info("\n🚀 Training Starter Tier Models")
        logger.info("-" * 40)

        starter_results = {}

        # 1. Content-Based Model (requires audio features)
        if self.audio_features:
            try:
                logger.info("Training Content-Based Model...")
                content_trainer = ContentBasedTrainer(Config.STARTER_MODELS.get('content_based', {}))
                content_results = content_trainer.train(self.audio_features)
                starter_results['content_based'] = content_results
                logger.info("✅ Content-Based Model training completed")
            except Exception as e:
                logger.error(f"❌ Content-Based Model training failed: {e}")
                starter_results['content_based'] = {'error': str(e)}
        else:
            logger.warning("⚠️ Skipping Content-Based Model (no audio features)")
            starter_results['content_based'] = {'error': 'No audio features available'}

        # 2. Daily Mix Generator (requires genre data)
        try:
            logger.info("Training Daily Mix Generator...")
            from models.premium.daily_mix_generator import DailyMixGenerator

            daily_mix = DailyMixGenerator()
            daily_mix.fit(self.train_data, self.tracks)

            # Save model
            model_path = os.path.join(Config.MODEL_SAVE_PATH, "starter", "daily_mix.pkl")
            os.makedirs(os.path.dirname(model_path), exist_ok=True)
            daily_mix.save(model_path)

            starter_results['daily_mix'] = {
                'model_type': 'Daily Mix Generator',
                'num_genres': len(daily_mix.genre_tracks),
                'num_users_with_history': len(daily_mix.user_genre_history),
                'training_time': 'completed'
            }
            logger.info("✅ Daily Mix Generator training completed")

        except Exception as e:
            logger.error(f"❌ Daily Mix Generator training failed: {e}")
            starter_results['daily_mix'] = {'error': str(e)}

        self.training_results['starter_tier'] = starter_results

    async def _train_pro_tier(self):
        """Train all Pro Tier models."""
        logger.info("\n💎 Training Pro Tier Models")
        logger.info("-" * 40)

        pro_results = {}

        # 1. Neural Collaborative Filtering
        try:
            logger.info("Training Neural Collaborative Filtering...")
            ncf_trainer = NeuralCFTrainer(Config.PRO_MODELS.get('neural_cf', {}))
            ncf_results = ncf_trainer.train(self.train_data, self.val_data)
            pro_results['neural_cf'] = ncf_results
            logger.info("✅ Neural CF training completed")
        except Exception as e:
            logger.error(f"❌ Neural CF training failed: {e}")
            pro_results['neural_cf'] = {'error': str(e)}

        # 2. Taste Profiler
        try:
            logger.info("Training Taste Profiler...")
            from models.enterprise.taste_profiler import TasteProfiler

            profiler = TasteProfiler()

            # Build profiles for a sample of users (for demonstration)
            sample_users = list(set(i['user_id'] for i in self.train_data))[:100]
            profiles_built = 0

            for user_id in sample_users:
                try:
                    user_interactions = [i for i in self.train_data if i['user_id'] == user_id]
                    if len(user_interactions) >= 5:  # Minimum interactions for profile
                        profile = profiler.build_profile(
                            user_id, user_interactions, self.tracks,
                            {f['track_id']: f for f in self.audio_features}
                        )
                        profiles_built += 1
                except Exception as e:
                    logger.debug(f"Failed to build profile for user {user_id}: {e}")

            # Save model
            model_path = os.path.join(Config.MODEL_SAVE_PATH, "pro", "taste_profiler.pkl")
            os.makedirs(os.path.dirname(model_path), exist_ok=True)
            profiler.save(model_path)

            pro_results['taste_profiler'] = {
                'model_type': 'Taste Profiler',
                'profiles_built': profiles_built,
                'sample_users': len(sample_users),
                'training_time': 'completed'
            }
            logger.info(f"✅ Taste Profiler training completed ({profiles_built} profiles)")

        except Exception as e:
            logger.error(f"❌ Taste Profiler training failed: {e}")
            pro_results['taste_profiler'] = {'error': str(e)}

        self.training_results['pro_tier'] = pro_results

    async def _run_evaluation(self):
        """Run comprehensive model evaluation."""
        logger.info("\n📈 Running Model Evaluation")
        logger.info("-" * 40)

        try:
            evaluator = ModelEvaluator()
            evaluation_results = await evaluator.run_evaluation_pipeline()
            self.training_results['evaluation'] = evaluation_results
            logger.info("✅ Model evaluation completed")

            # Log key metrics
            if 'summary' in evaluation_results:
                summary = evaluation_results['summary']
                if 'best_models' in summary:
                    logger.info("🏆 Best performing models:")
                    for metric, info in summary['best_models'].items():
                        logger.info(f"  {metric}: {info['model']} (score: {info['score']:.4f})")

        except Exception as e:
            logger.error(f"❌ Model evaluation failed: {e}")
            self.training_results['evaluation'] = {'error': str(e)}

    def _generate_final_report(self):
        """Generate and log final training report."""
        duration = datetime.now() - self.start_time

        logger.info("\n" + "=" * 60)
        logger.info("🎉 TRAINING PIPELINE COMPLETE")
        logger.info("=" * 60)
        logger.info(f"Total duration: {duration}")

        # Count successful/failed models
        total_models = 0
        successful_models = 0
        failed_models = 0

        for tier_name, tier_results in self.training_results.items():
            if tier_name == 'evaluation':
                continue

            for model_name, model_results in tier_results.items():
                total_models += 1
                if 'error' in model_results:
                    failed_models += 1
                    logger.error(f"❌ {tier_name}/{model_name}: {model_results['error']}")
                else:
                    successful_models += 1
                    logger.info(f"✅ {tier_name}/{model_name}: Success")

        logger.info(f"\nSummary: {successful_models}/{total_models} models trained successfully")

        if failed_models > 0:
            logger.warning(f"⚠️ {failed_models} models failed to train")

        # Save training report
        self._save_training_report()

    def _save_training_report(self):
        """Save training report to file."""
        try:
            import json

            report = {
                'training_date': self.start_time.isoformat(),
                'duration_seconds': (datetime.now() - self.start_time).total_seconds(),
                'config': {
                    'force_retrain': self.force_retrain,
                    'gpu_enabled': Config.ENABLE_GPU,
                },
                'data_summary': {
                    'train_interactions': len(self.train_data) if hasattr(self, 'train_data') else 0,
                    'val_interactions': len(self.val_data) if hasattr(self, 'val_data') else 0,
                    'total_tracks': len(self.tracks) if hasattr(self, 'tracks') else 0,
                    'tracks_with_audio': len(self.audio_features) if hasattr(self, 'audio_features') else 0,
                },
                'results': self.training_results
            }

            report_path = os.path.join(Config.MODEL_SAVE_PATH, f"training_report_{self.start_time.strftime('%Y%m%d_%H%M%S')}.json")
            os.makedirs(os.path.dirname(report_path), exist_ok=True)

            with open(report_path, 'w') as f:
                json.dump(report, f, indent=2, default=str)

            logger.info(f"📄 Training report saved to: {report_path}")

        except Exception as e:
            logger.error(f"Failed to save training report: {e}")


async def main():
    """Main function to run the training pipeline."""
    parser = argparse.ArgumentParser(description='Train TuneTrail ML Models')
    parser.add_argument(
        '--tier',
        choices=['free', 'starter', 'pro', 'all'],
        default='all',
        help='Which tier to train (default: all)'
    )
    parser.add_argument(
        '--force',
        action='store_true',
        help='Force retrain even if models exist'
    )
    parser.add_argument(
        '--evaluate',
        action='store_true',
        help='Run evaluation after training'
    )

    args = parser.parse_args()

    # Determine tiers to train
    if args.tier == 'all':
        tiers = ['free', 'starter', 'pro']
    else:
        tiers = [args.tier]

    try:
        # Initialize and run training pipeline
        pipeline = TrainingPipeline(force_retrain=args.force)
        results = await pipeline.run_complete_training(tiers=tiers, evaluate=args.evaluate)

        # Exit with appropriate code
        has_errors = any(
            'error' in model_result
            for tier_results in results.values()
            for model_result in (tier_results.values() if isinstance(tier_results, dict) else [])
            if isinstance(model_result, dict)
        )

        if has_errors:
            logger.error("Training completed with errors")
            sys.exit(1)
        else:
            logger.info("All training completed successfully! 🎉")
            sys.exit(0)

    except KeyboardInterrupt:
        logger.info("Training interrupted by user")
        sys.exit(130)
    except Exception as e:
        logger.error(f"Training pipeline failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())