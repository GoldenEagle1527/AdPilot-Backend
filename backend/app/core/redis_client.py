from __future__ import annotations

from redis.asyncio import Redis

from app.core.config import Settings, get_settings

_redis: Redis | None = None


def init_redis(settings: Settings | None = None) -> Redis:
    global _redis
    settings = settings or get_settings()
    _redis = Redis(
        host=settings.redis.host,
        port=settings.redis.port,
        password=settings.redis.password or None,
        decode_responses=True,
        socket_connect_timeout=3,
        socket_timeout=3,
    )
    return _redis


def get_redis() -> Redis:
    if _redis is None:
        init_redis()
    assert _redis is not None
    return _redis


async def close_redis() -> None:
    global _redis
    if _redis is not None:
        await _redis.aclose()
    _redis = None


async def redis_ready() -> tuple[bool, str]:
    try:
        client = get_redis()
        await client.ping()
        info = await client.info("server")
        version = str(info.get("redis_version", ""))
        if not version.startswith("7.2."):
            return False, f"Redis 须为 7.2.x，当前 {version or '未知'}"
        return True, version
    except Exception as exc:
        return False, f"无法连接 Redis：{exc}"
