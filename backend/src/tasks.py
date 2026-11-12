"""Celery 任务：心跳（供 worker healthcheck）+ 每日自动巡检 + 违约检测。"""
from __future__ import annotations

import time

from src.config.celery_app import (
    TASK_DAILY_PROBE,
    TASK_DETECT_BREACHES,
    TASK_HEARTBEAT,
    celery_app,
)
from src.config.settings import settings
from src.utils.logger import get_logger

logger = get_logger("tasks")
HEARTBEAT_KEY = "freshsla:worker:heartbeat"


@celery_app.task(name=TASK_HEARTBEAT)
def heartbeat() -> dict:
    import redis

    client = redis.Redis.from_url(settings.redis_url, decode_responses=True)
    client.set(HEARTBEAT_KEY, str(time.time()), ex=300)
    return {"heartbeat": time.time()}


@celery_app.task(name=TASK_DAILY_PROBE)
def daily_probe() -> dict:
    """每天 08:10 自动跑一次巡检 + 违约检测（与 api 触发同一套服务）。"""
    from src.config.database import session_scope
    from src.services import breach_service, probe_service

    with session_scope() as db:
        result = probe_service.run(db, actor_email="celery@freshsla.io", trigger_source="beat")
        detection = breach_service.detect(db)
    logger.info("[BEAT] probe %s / breaches +%s", result["run_date"], detection["created"])
    return {"probe": result, "breach": detection}


@celery_app.task(name=TASK_DETECT_BREACHES)
def detect_breaches(days: int = 30) -> dict:
    from src.config.database import session_scope
    from src.services import breach_service

    with session_scope() as db:
        return breach_service.detect(db, days=days)
