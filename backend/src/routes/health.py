"""健康检查：DB / Redis 连通性 + 业务水位。"""
from __future__ import annotations

from fastapi import APIRouter

from src.config.database import ping_db
from src.config.settings import settings
from src.utils.timeutil import business_now

router = APIRouter(tags=["health"])


def _ping_redis() -> bool:
    try:
        import redis

        client = redis.Redis.from_url(settings.redis_url, socket_connect_timeout=2)
        return bool(client.ping())
    except Exception:
        return False


@router.get("/health")
def health():
    db_ok = ping_db()
    redis_ok = _ping_redis()
    return {
        "status": "ok" if db_ok else "degraded",
        "brand": settings.app_name,
        "db": db_ok,
        "redis": redis_ok,
        "version": "1.0.0",
        "server_time": business_now().isoformat(sep=" "),
        "calibration_days": settings.calibration_days,
    }


@router.get("/meta/enums")
def enums():
    from src.constants.enums import (
        GRADE_LABELS,
        HANDLING_LABELS,
        LAYER_LABELS,
        SEVERITY_LABELS,
        BreachSeverity,
        Grade,
        HandlingStatus,
        Layer,
        ProbeStatus,
        Role,
        Tier,
    )

    return {
        "roles": [item.value for item in Role],
        "layers": [{"value": item.value, "label": LAYER_LABELS[item.value]} for item in Layer],
        "tiers": [item.value for item in Tier],
        "grades": [{"value": item.value, "label": GRADE_LABELS[item.value]} for item in Grade],
        "probe_status": [item.value for item in ProbeStatus],
        "severities": [{"value": item.value, "label": SEVERITY_LABELS[item.value]} for item in BreachSeverity],
        "handling": [{"value": item.value, "label": HANDLING_LABELS[item.value]} for item in HandlingStatus],
    }
