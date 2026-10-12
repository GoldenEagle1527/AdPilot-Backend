"""端原生自动化投放执行记录的表查询。"""

from __future__ import annotations

from sqlalchemy import ColumnElement, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import Select

from app.modules.uni_native_auto_run.model import UniNativeAutoRun, UniNativeAutoRunFailure


def get_run_stmt(run_id: int) -> Select[tuple[UniNativeAutoRun]]:
    """一条未删除的执行记录。"""
    return select(UniNativeAutoRun).where(UniNativeAutoRun.id == run_id, UniNativeAutoRun.is_deleted == 0)


async def get_run(session: AsyncSession, run_id: int) -> UniNativeAutoRun | None:
    """取一条未删除的执行记录。"""
    result = await session.execute(get_run_stmt(run_id))
    return result.scalar_one_or_none()


def page_runs_stmt(
    filters: list[ColumnElement[bool]], *, offset: int, limit: int
) -> Select[tuple[UniNativeAutoRun]]:
    """按执行时间倒序的分页查询。"""
    return (
        select(UniNativeAutoRun)
        .where(*filters)
        .order_by(UniNativeAutoRun.executed_at.desc(), UniNativeAutoRun.id.desc())
        .offset(offset)
        .limit(limit)
    )


async def page_runs(
    session: AsyncSession,
    filters: list[ColumnElement[bool]],
    *,
    offset: int,
    limit: int,
) -> tuple[list[UniNativeAutoRun], int]:
    """按执行时间倒序分页。返回 (行, 总数)。"""
    total = int(
        (await session.execute(select(func.count()).select_from(UniNativeAutoRun).where(*filters))).scalar_one()
    )
    result = await session.execute(page_runs_stmt(filters, offset=offset, limit=limit))
    return list(result.scalars().all()), total


def page_failures_stmt(run_id: int, *, offset: int, limit: int) -> Select[tuple[UniNativeAutoRunFailure]]:
    """一条执行记录下未删除的失败日志，按写入顺序。"""
    return (
        select(UniNativeAutoRunFailure)
        .where(UniNativeAutoRunFailure.run_id == run_id, UniNativeAutoRunFailure.is_deleted == 0)
        .order_by(UniNativeAutoRunFailure.id.asc())
        .offset(offset)
        .limit(limit)
    )


async def page_failures(
    session: AsyncSession, run_id: int, *, offset: int, limit: int
) -> tuple[list[UniNativeAutoRunFailure], int]:
    """分页一条执行记录的失败日志。返回 (行, 总数)。"""
    alive = (UniNativeAutoRunFailure.run_id == run_id, UniNativeAutoRunFailure.is_deleted == 0)
    total = int(
        (await session.execute(select(func.count()).select_from(UniNativeAutoRunFailure).where(*alive))).scalar_one()
    )
    result = await session.execute(page_failures_stmt(run_id, offset=offset, limit=limit))
    return list(result.scalars().all()), total
