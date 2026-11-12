"""通用响应模型。"""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class ErrorResponse(BaseModel):
    code: str = Field(description="错误码，如 FORBIDDEN / VALIDATION")
    message: str
    detail: Any | None = None


class HealthResponse(BaseModel):
    status: str
    brand: str
    db: bool
    redis: bool
    version: str
    server_time: str
    calibration_days: int
