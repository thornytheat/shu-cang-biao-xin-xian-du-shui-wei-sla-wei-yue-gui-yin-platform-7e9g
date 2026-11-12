"""限流中间件：Redis 固定窗口；写接口单独额度（探测/检测/导出相对昂贵）。"""
from __future__ import annotations

import time

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from src.config.settings import settings
from src.constants.limits import RATE_WINDOW_SECONDS
from src.utils.logger import get_logger

logger = get_logger("rate_limit")
SKIP_PATHS = {"/api/health", "/health"}
WRITE_BUCKET_PREFIXES = ("/api/probes/run", "/api/breaches", "/api/policies", "/api/exports")


class RateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        if path in SKIP_PATHS:
            return await call_next(request)
        try:
            import redis

            client = redis.Redis.from_url(settings.redis_url, decode_responses=True, socket_connect_timeout=2)
            is_write = request.method in {"POST", "PATCH", "PUT", "DELETE"} and path.startswith(
                WRITE_BUCKET_PREFIXES
            )
            limit = settings.rate_limit_write_per_minute if is_write else settings.rate_limit_per_minute
            scope = "write" if is_write else "default"
            ip = request.client.host if request.client else "unknown"
            window = int(time.time() // RATE_WINDOW_SECONDS)
            key = f"freshsla:rl:{scope}:{ip}:{window}"
            count = client.incr(key)
            if count == 1:
                client.expire(key, RATE_WINDOW_SECONDS + 2)
            if count > limit:
                return JSONResponse(
                    status_code=429,
                    content={
                        "code": "RATE_LIMITED",
                        "message": "请求过于频繁，请稍后再试",
                        "detail": {"limit": limit, "scope": scope},
                    },
                    headers={"Retry-After": str(RATE_WINDOW_SECONDS)},
                )
        except Exception as exc:  # noqa: BLE001 - 限流降级不影响主流程
            logger.debug("rate limit degraded: %s", exc)
        return await call_next(request)
