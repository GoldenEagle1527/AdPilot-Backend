from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from app.core.db import postgres_ready
from app.core.envelope import Envelope, failure, success
from app.core.redis_client import redis_ready

router = APIRouter(prefix="/api/v1", tags=["health"])


class HealthData(BaseModel):
    status: str


class ReadyData(BaseModel):
    status: str
    postgres: str
    redis: str


@router.get("/health", response_model=Envelope[HealthData])
async def health() -> dict:
    return success({"status": "ok"})


@router.get("/ready", response_model=Envelope[ReadyData])
async def ready():
    pg_ok, pg_msg = await postgres_ready()
    redis_ok, redis_msg = await redis_ready()
    if pg_ok and redis_ok:
        return success(
            {
                "status": "ok",
                "postgres": pg_msg,
                "redis": redis_msg,
            }
        )
    parts = []
    if not pg_ok:
        parts.append(pg_msg)
    if not redis_ok:
        parts.append(redis_msg)
    return JSONResponse(
        status_code=503,
        content=failure(503, "；".join(parts)),
    )
