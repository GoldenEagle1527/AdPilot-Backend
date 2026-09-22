"""Celery 应用。启动：celery -A app.tasks.celery_app。"""

from __future__ import annotations

from urllib.parse import quote_plus

from celery import Celery

from app.core.config import get_settings


def _redis_url(db: int) -> str:
    """拼 Redis URL。登录态在 0 号库，broker 用 1，结果用 2。"""
    settings = get_settings()
    auth = ""
    if settings.redis.password:
        auth = f":{quote_plus(settings.redis.password)}@"
    return f"redis://{auth}{settings.redis.host}:{settings.redis.port}/{db}"


CELERY_BROKER_URL = _redis_url(1)
CELERY_BACKEND_URL = _redis_url(2)

celery_app = Celery(
    "adpilot",
    broker=CELERY_BROKER_URL,
    backend=CELERY_BACKEND_URL,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Shanghai",
    enable_utc=True,
    worker_prefetch_multiplier=1,  # 一次只领一条
    result_expires=86400,
    broker_connection_retry_on_startup=True,
    task_default_queue="manhua_sync",
    task_routes={
        "app.tasks.sync_manhua_tasks.sync_aweme_series": {"queue": "manhua_sync"},
    },
    task_acks_late=True,  # 执行完再 ack，worker 中途挂了会重投
    task_reject_on_worker_lost=True,
    task_soft_time_limit=60,
    task_time_limit=90,
)

celery_app.conf.include = [
    "app.tasks.sync_manhua_tasks",
]

# Beat：按最晚创建时间拉常读短剧 100 条，每 1 分钟
celery_app.conf.beat_schedule = {
    "sync-aweme-series-every-1min": {
        "task": "app.tasks.sync_manhua_tasks.sync_aweme_series",
        "schedule": 60.0,
    },
}
