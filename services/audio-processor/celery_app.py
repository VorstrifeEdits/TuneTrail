"""
TuneTrail Celery Application Configuration
Handles background audio processing tasks
"""

import os
from celery import Celery

# Celery configuration
BROKER_URL = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/1")
RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/2")

# Create Celery app
app = Celery(
    "tunetrail_audio_processor",
    broker=BROKER_URL,
    backend=RESULT_BACKEND,
    include=["tasks"]  # Include tasks module
)

# Celery configuration
app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    worker_log_format="[%(asctime)s: %(levelname)s/%(processName)s] %(message)s",
    worker_task_log_format="[%(asctime)s: %(levelname)s/%(processName)s][%(task_name)s(%(task_id)s)] %(message)s",
    task_routes={
        "tasks.process_audio": {"queue": "audio_processing"},
        "tasks.extract_features": {"queue": "feature_extraction"},
    },
)

if __name__ == "__main__":
    app.start()