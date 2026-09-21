from __future__ import annotations

from collections.abc import AsyncIterator
from datetime import datetime

from sqlalchemy import DateTime, Identity, Integer, func, text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from app.core.config import Settings, get_settings
from app.core.times import beijing_now

_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None

_TS = DateTime(timezone=True)


class BaseModel(DeclarativeBase):
    """业务表公共列：自增主键、软删除、创建/更新时间（北京时间）。"""

    __abstract__ = True

    id: Mapped[int] = mapped_column(Integer, Identity(), primary_key=True, comment="库内自增主键")
    is_deleted: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0", comment="是否删除：0 否、1 是"
    )
    deleted_at: Mapped[datetime | None] = mapped_column(_TS, nullable=True, comment="删除时间，未删为空")
    created_date: Mapped[datetime] = mapped_column(
        _TS, nullable=False, server_default=func.now(), comment="创建时间（北京）"
    )
    updated_date: Mapped[datetime] = mapped_column(
        _TS, nullable=False, server_default=func.now(), onupdate=func.now(), comment="更新时间（北京）"
    )

    def mark_deleted(self) -> None:
        """标成软删除。"""
        self.is_deleted = 1
        self.deleted_at = beijing_now()


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
