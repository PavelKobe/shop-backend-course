from celery import Celery

from app.core.config import get_settings

settings = get_settings()

celery_app = Celery(
    "shop",
    broker=settings.broker_url,
    backend=settings.result_backend,
)
celery_app.conf.task_track_started = True
# чтобы Celery нашёл задачи
celery_app.conf.imports = ("app.tasks.email",)

import app.tasks.email  # noqa: E402,F401
