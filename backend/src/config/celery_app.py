"""Celery 入口：backend 投递任务，worker 容器消费（心跳 + 每日新鲜度巡检）。"""
from __future__ import annotations

from celery import Celery
from celery.schedules import crontab

from src.config.settings import settings

celery_app = Celery(
    "freshsla",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=["src.tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="Asia/Shanghai",
    enable_utc=False,
    task_track_started=True,
    result_expires=3600,
    broker_connection_retry_on_startup=True,
    worker_hijack_root_logger=False,
)

celery_app.conf.beat_schedule = {
    "freshsla-heartbeat": {"task": "freshsla.heartbeat", "schedule": 20.0},
    "freshsla-daily-probe": {"task": "freshsla.daily_probe", "schedule": crontab(hour="8", minute="10")},
}

TASK_HEARTBEAT = "freshsla.heartbeat"
TASK_DAILY_PROBE = "freshsla.daily_probe"
TASK_DETECT_BREACHES = "freshsla.detect_breaches"
