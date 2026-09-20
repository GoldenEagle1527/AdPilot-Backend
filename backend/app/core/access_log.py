from __future__ import annotations

import logging
import time

from fastapi import FastAPI, Request

logger = logging.getLogger("adpilot")


def apply_access_log(app: FastAPI) -> None:
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter("%(asctime)s %(name)s %(message)s"))
        logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    logger.propagate = False

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
