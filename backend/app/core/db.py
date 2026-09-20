from __future__ import annotations

from collections.abc import AsyncIterator

from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.core.config import Settings, get_settings

_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


class Base(DeclarativeBase):
    pass


def init_engine(settings: Settings | None = None) -> AsyncEngine:
    global _engine, _session_factory
    settings = settings or get_settings()
    _engine = create_async_engine(
        settings.async_database_url,
        pool_pre_ping=True,
        pool_size=settings.db_pool_size,
        max_overflow=settings.db_pool_max_overflow,
        pool_timeout=settings.db_pool_timeout,
        connect_args={"timeout": 3},
    )
    _session_factory = async_sessionmaker(_engine, expire_on_commit=False)
    return _engine


def get_engine() -> AsyncEngine:
    if _engine is None:
        init_engine()
    assert _engine is not None
    return _engine


async def dispose_engine() -> None:
    global _engine, _session_factory
    if _engine is not None:
        await _engine.dispose()
    _engine = None
    _session_factory = None


async def get_session() -> AsyncIterator[AsyncSession]:
    if _session_factory is None:
        init_engine()
    assert _session_factory is not None
    async with _session_factory() as session:
        yield session


async def postgres_ready() -> tuple[bool, str]:
    try:
        async with get_engine().connect() as conn:
            result = await conn.execute(text("SHOW server_version"))
            version = str(result.scalar_one())
        if not version.startswith("18."):
            return False, f"PostgreSQL 主版本须为 18.x，当前 {version}"
        return True, version
    except Exception as exc:
        return False, f"无法连接 PostgreSQL：{exc}"
