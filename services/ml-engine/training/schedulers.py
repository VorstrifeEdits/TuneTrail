import asyncio
import schedule
import time
from datetime import datetime, timedelta
from typing import Dict, List
import logging
from enum import Enum


class TrainingPriority(Enum):
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4


class TrainingJob:
    """Represents a training job with metadata."""

    def __init__(
        self,
        name: str,
        tier: str,
        trainer_class: str,
        priority: TrainingPriority = TrainingPriority.MEDIUM,
        estimated_duration_minutes: int = 30,
        dependencies: List[str] = None
    ):
        self.name = name
        self.tier = tier
        self.trainer_class = trainer_class
        self.priority = priority
        self.estimated_duration_minutes = estimated_duration_minutes
        self.dependencies = dependencies or []
        self.last_run = None
        self.last_success = None
        self.is_running = False
        self.run_count = 0
        self.failure_count = 0


class TrainingScheduler:
    """Manages training schedules for all ML models."""

    def __init__(self):
        self.logger = logging.getLogger("scheduler")
        self.jobs = {}
        self.active_jobs = set()
        self.job_history = []

        self._setup_training_jobs()

    def _setup_training_jobs(self):
        """Setup all training jobs with their schedules."""

        # Free Tier Jobs (Run daily at 4am)
        self.jobs['collaborative_filter'] = TrainingJob(
            name='collaborative_filter',
            tier='free',
            trainer_class='CollaborativeFilterTrainer',
            priority=TrainingPriority.HIGH,
            estimated_duration_minutes=30,
        )

        self.jobs['popularity'] = TrainingJob(
            name='popularity',
            tier='free',
            trainer_class='PopularityTrainer',
            priority=TrainingPriority.MEDIUM,
            estimated_duration_minutes=10,
        )

        self.jobs['genre_based'] = TrainingJob(
            name='genre_based',
            tier='free',
            trainer_class='GenreBasedTrainer',
            priority=TrainingPriority.MEDIUM,
            estimated_duration_minutes=15,
        )

        # Starter Tier Jobs (Run daily at 5am)
        self.jobs['content_based'] = TrainingJob(
            name='content_based',
            tier='starter',
            trainer_class='ContentBasedTrainer',
            priority=TrainingPriority.HIGH,
            estimated_duration_minutes=60,
        )

        self.jobs['daily_mix'] = TrainingJob(
            name='daily_mix',
            tier='starter',
            trainer_class='DailyMixTrainer',
            priority=TrainingPriority.MEDIUM,
            estimated_duration_minutes=20,
            dependencies=['collaborative_filter', 'genre_based']
        )

        # Pro Tier Jobs (Run daily at 7am)
        self.jobs['neural_cf'] = TrainingJob(
            name='neural_cf',
            tier='pro',
            trainer_class='NeuralCFTrainer',
            priority=TrainingPriority.HIGH,
            estimated_duration_minutes=180,
            dependencies=['collaborative_filter']
        )

        self.jobs['taste_profiler'] = TrainingJob(
            name='taste_profiler',
            tier='pro',
            trainer_class='TasteProfilerTrainer',
            priority=TrainingPriority.MEDIUM,
            estimated_duration_minutes=30,
            dependencies=['collaborative_filter', 'content_based']
        )

        # Evaluation Job (Run daily at 10am)
        self.jobs['model_evaluation'] = TrainingJob(
            name='model_evaluation',
            tier='evaluation',
            trainer_class='ModelEvaluator',
            priority=TrainingPriority.CRITICAL,
            estimated_duration_minutes=45,
            dependencies=['collaborative_filter', 'neural_cf', 'content_based']
        )

    def setup_schedules(self):
        """Setup cron-like schedules for all training jobs."""

        # Free tier models - 4:00 AM daily
        schedule.every().day.at("04:00").do(
            self._run_tier_jobs, tier='free'
        ).tag('free_tier')

        # Starter tier models - 5:00 AM daily
        schedule.every().day.at("05:00").do(
            self._run_tier_jobs, tier='starter'
        ).tag('starter_tier')

        # Pro tier models - 7:00 AM daily
        schedule.every().day.at("07:00").do(
            self._run_tier_jobs, tier='pro'
        ).tag('pro_tier')

        # Model evaluation - 10:00 AM daily
        schedule.every().day.at("10:00").do(
            self._run_evaluation
        ).tag('evaluation')

        # Index building - 12:00 PM daily
        schedule.every().day.at("12:00").do(
            self._rebuild_indexes
        ).tag('indexing')

        self.logger.info("Training schedules configured:")
        self.logger.info("  04:00 - Free tier models (CF, Popularity, Genre)")
        self.logger.info("  05:00 - Starter tier models (Content-based, Daily Mix)")
        self.logger.info("  07:00 - Pro tier models (Neural CF, Taste Profiler)")
        self.logger.info("  10:00 - Model evaluation")
        self.logger.info("  12:00 - Index rebuilding")

    async def _run_tier_jobs(self, tier: str):
        """Run all jobs for a specific tier."""
        self.logger.info(f"Starting {tier} tier training jobs...")

        tier_jobs = [job for job in self.jobs.values() if job.tier == tier]
        tier_jobs.sort(key=lambda x: x.priority.value, reverse=True)

        for job in tier_jobs:
            if await self._can_run_job(job):
                await self._execute_job(job)

        self.logger.info(f"Completed {tier} tier training jobs")

    async def _can_run_job(self, job: TrainingJob) -> bool:
        """Check if a job can be run (dependencies, resources, etc.)."""
        if job.is_running:
            self.logger.warning(f"Job {job.name} is already running")
            return False

        # Check dependencies
        for dep_name in job.dependencies:
            if dep_name in self.jobs:
                dep_job = self.jobs[dep_name]
                if dep_job.last_success is None:
                    self.logger.warning(f"Job {job.name} dependency {dep_name} has never run successfully")
                    return False

                # Check if dependency ran recently (within last 24 hours)
                if dep_job.last_success < datetime.now() - timedelta(hours=24):
                    self.logger.warning(f"Job {job.name} dependency {dep_name} is stale")
                    return False

        # Check system resources (simplified)
        if len(self.active_jobs) >= 2:  # Max 2 concurrent jobs
            self.logger.warning(f"Too many active jobs, skipping {job.name}")
            return False

        return True

    async def _execute_job(self, job: TrainingJob):
        """Execute a training job."""
        self.logger.info(f"Starting job: {job.name} (tier: {job.tier})")

        job.is_running = True
        job.last_run = datetime.now()
        self.active_jobs.add(job.name)

        start_time = time.time()
        success = False

        try:
            # Execute the actual training
            await self._run_training_job(job)
            success = True
            job.last_success = datetime.now()
            job.run_count += 1

            self.logger.info(f"Job {job.name} completed successfully")

        except Exception as e:
            job.failure_count += 1
            self.logger.error(f"Job {job.name} failed: {e}")

        finally:
            job.is_running = False
            self.active_jobs.discard(job.name)

            # Record job history
            duration_minutes = (time.time() - start_time) / 60
            self.job_history.append({
                'job_name': job.name,
                'tier': job.tier,
                'start_time': job.last_run,
                'duration_minutes': duration_minutes,
                'success': success,
                'estimated_duration': job.estimated_duration_minutes
            })

            # Keep only last 100 job records
            if len(self.job_history) > 100:
                self.job_history = self.job_history[-100:]

    async def _run_training_job(self, job: TrainingJob):
        """Run the actual training job."""
        from training.trainers import (
            CollaborativeFilterTrainer,
            PopularityTrainer,
            GenreBasedTrainer,
            ContentBasedTrainer,
            NeuralCFTrainer
        )
        from training.evaluators import ModelEvaluator
        from data.loaders import load_training_data, load_tracks, load_audio_features
        from config import Config

        # Load data based on job type
        if job.name in ['collaborative_filter', 'popularity', 'genre_based', 'neural_cf']:
            train_data, val_data = await load_training_data(train_ratio=0.8)

        if job.name == 'genre_based':
            tracks = await load_tracks()

        if job.name == 'content_based':
            audio_features = await load_audio_features()

        # Initialize trainer
        trainer_config = Config.FREE_MODELS.get(job.name, {})
        if job.tier == 'starter':
            trainer_config = Config.STARTER_MODELS.get(job.name, {})
        elif job.tier == 'pro':
            trainer_config = Config.PRO_MODELS.get(job.name, {})

        # Execute training based on job type
        if job.name == 'collaborative_filter':
            trainer = CollaborativeFilterTrainer(trainer_config)
            await asyncio.get_event_loop().run_in_executor(
                None, trainer.train, train_data, val_data
            )

        elif job.name == 'popularity':
            trainer = PopularityTrainer(trainer_config)
            await asyncio.get_event_loop().run_in_executor(
                None, trainer.train, train_data, val_data
            )

        elif job.name == 'genre_based':
            trainer = GenreBasedTrainer(trainer_config)
            await asyncio.get_event_loop().run_in_executor(
                None, trainer.train, train_data, tracks, val_data
            )

        elif job.name == 'content_based':
            trainer = ContentBasedTrainer(trainer_config)
            await asyncio.get_event_loop().run_in_executor(
                None, trainer.train, audio_features
            )

        elif job.name == 'neural_cf':
            trainer = NeuralCFTrainer(trainer_config)
            await asyncio.get_event_loop().run_in_executor(
                None, trainer.train, train_data, val_data
            )

        elif job.name == 'model_evaluation':
            evaluator = ModelEvaluator()
            await evaluator.run_evaluation_pipeline()

        else:
            raise ValueError(f"Unknown job type: {job.name}")

    async def _run_evaluation(self):
        """Run model evaluation."""
        eval_job = self.jobs['model_evaluation']
        if await self._can_run_job(eval_job):
            await self._execute_job(eval_job)

    async def _rebuild_indexes(self):
        """Rebuild FAISS indexes."""
        self.logger.info("Rebuilding FAISS indexes...")

        try:
            from utils.similarity import build_faiss_index
            from data.loaders import load_audio_features
            from config import Config
            import os
            import numpy as np

            # Load audio features
            audio_features = await load_audio_features()

            if audio_features:
                embeddings = np.array([f['embedding'] for f in audio_features if f['embedding']])

                if len(embeddings) > 0:
                    # Build FAISS index
                    index = build_faiss_index(
                        embeddings,
                        use_gpu=Config.ENABLE_GPU,
                        nlist=Config.FAISS_NLIST
                    )

                    # Save index
                    index_path = os.path.join(Config.FAISS_INDEX_PATH, "audio_features.index")
                    os.makedirs(os.path.dirname(index_path), exist_ok=True)

                    import faiss
                    faiss.write_index(index, index_path)

                    self.logger.info(f"FAISS index rebuilt with {len(embeddings)} vectors")

        except Exception as e:
            self.logger.error(f"Failed to rebuild indexes: {e}")

    def run_scheduler(self):
        """Run the training scheduler continuously."""
        self.logger.info("Starting training scheduler...")

        while True:
            schedule.run_pending()
            time.sleep(60)  # Check every minute

    def get_job_status(self) -> Dict:
        """Get status of all jobs."""
        status = {
            'active_jobs': list(self.active_jobs),
            'job_summary': {},
            'recent_history': self.job_history[-10:] if self.job_history else []
        }

        for name, job in self.jobs.items():
            status['job_summary'][name] = {
                'tier': job.tier,
                'priority': job.priority.name,
                'is_running': job.is_running,
                'last_run': job.last_run.isoformat() if job.last_run else None,
                'last_success': job.last_success.isoformat() if job.last_success else None,
                'run_count': job.run_count,
                'failure_count': job.failure_count,
                'estimated_duration_minutes': job.estimated_duration_minutes
            }

        return status

    async def trigger_manual_training(self, job_name: str) -> Dict:
        """Manually trigger a training job."""
        if job_name not in self.jobs:
            return {'error': f'Job {job_name} not found'}

        job = self.jobs[job_name]

        if job.is_running:
            return {'error': f'Job {job_name} is already running'}

        self.logger.info(f"Manually triggering job: {job_name}")

        try:
            await self._execute_job(job)
            return {'success': f'Job {job_name} completed successfully'}
        except Exception as e:
            return {'error': f'Job {job_name} failed: {str(e)}'}

    def stop_scheduler(self):
        """Stop the scheduler gracefully."""
        self.logger.info("Stopping training scheduler...")
        schedule.clear()

        # Wait for active jobs to complete (with timeout)
        timeout = 300  # 5 minutes
        while self.active_jobs and timeout > 0:
            time.sleep(5)
            timeout -= 5

        if self.active_jobs:
            self.logger.warning(f"Active jobs still running: {self.active_jobs}")

        self.logger.info("Training scheduler stopped")