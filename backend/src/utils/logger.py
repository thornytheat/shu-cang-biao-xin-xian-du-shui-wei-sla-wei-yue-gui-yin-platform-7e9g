"""日志工厂：统一前缀，便于 docker logs 过滤。"""
from __future__ import annotations

import logging
import sys

_CONFIGURED = False


def _configure() -> None:
    global _CONFIGURED
    if _CONFIGURED:
        return
    root = logging.getLogger("freshsla")
    if not root.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(logging.Formatter("[%(asctime)s] %(levelname)s %(name)s %(message)s"))
        root.addHandler(handler)
        root.setLevel(logging.INFO)
        root.propagate = False
    _CONFIGURED = True


def get_logger(name: str = "app") -> logging.Logger:
    _configure()
    return logging.getLogger(f"freshsla.{name}")
