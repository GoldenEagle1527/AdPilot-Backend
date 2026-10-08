"""访问日志和未捕获异常。控制台和 backend/logs/api.log 各写一份。"""

from __future__ import annotations

import logging
import time
from pathlib import Path

from fastapi import FastAPI, Request

logger = logging.getLogger("adpilot")

_FORMAT = "%(asctime)s %(levelname)s %(name)s %(message)s"


def api_log_path() -> Path:
    """backend/logs/api.log。"""
    return Path(__file__).resolve().parents[2] / "logs" / "api.log"


def api_log_config() -> dict:
    """uvicorn 用的日志配置：访问和错误同时进控制台和 api.log。"""
    path = api_log_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    return {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "default": {"format": _FORMAT},
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "formatter": "default",
            },
            "file": {
                "class": "logging.FileHandler",
                "formatter": "default",
                "filename": str(path),
                "encoding": "utf-8",
            },
        },
        "loggers": {
            "adpilot": {
                "handlers": ["console", "file"],
                "level": "INFO",
                "propagate": False,
            },
            "uvicorn": {
                "handlers": ["console", "file"],
                "level": "INFO",
                "propagate": False,
            },
            "uvicorn.error": {
                "handlers": ["console", "file"],
                "level": "INFO",
                "propagate": False,
            },
            "uvicorn.access": {
                "handlers": ["console", "file"],
                "level": "INFO",
                "propagate": False,
            },
        },
    }


def ensure_api_logger() -> None:
    """没走 uvicorn 配置时，仍把 adpilot 日志打到控制台和 api.log。"""
    if logger.handlers:
        return
    path = api_log_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    formatter = logging.Formatter(_FORMAT)
    stream = logging.StreamHandler()
    stream.setFormatter(formatter)
    file_handler = logging.FileHandler(path, encoding="utf-8")
    file_handler.setFormatter(formatter)
    logger.addHandler(stream)
    logger.addHandler(file_handler)
    logger.setLevel(logging.INFO)
    logger.propagate = False


def log_unhandled(exc: BaseException) -> None:
    """记下异常类型和堆栈。响应体里不放这些。"""
    ensure_api_logger()
    logger.error(
        "%s",
        type(exc).__name__,
        exc_info=(type(exc), exc, exc.__traceback__),
    )


def apply_access_log(app: FastAPI) -> None:
    """每个请求写一行：方法、路径、状态码、耗时。"""
    ensure_api_logger()

    @app.middleware("http")
    async def access_log(request: Request, call_next):
        started = time.perf_counter()
        response = await call_next(request)
        elapsed_ms = int((time.perf_counter() - started) * 1000)
        logger.info(
            "%s %s %s %sms",
            request.method,
            request.url.path,
            response.status_code,
            elapsed_ms,
        )
        return response
