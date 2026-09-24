"""漫剧表查询和写入。"""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from sqlalchemy import ColumnElement, func, select, tuple_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.times import beijing_now
from app.modules.material.model import ManhuaSeries


async def page_series(
    session: AsyncSession,
    filters: list[ColumnElement[bool]],
    *,
    offset: int,
    limit: int,
) -> tuple[list[ManhuaSeries], int]:
    """按采集时间倒序分页未删除行。返回 (行, 总数)。"""
    total = int(
        (
            await session.execute(select(func.count()).select_from(ManhuaSeries).where(*filters))
        ).scalar_one()
    )
    result = await session.execute(
        select(ManhuaSeries)
        .where(*filters)
        .order_by(ManhuaSeries.collected_at.desc(), ManhuaSeries.id.desc())
        .offset(offset)
        .limit(limit)
    )
    return list(result.scalars().all()), total


async def book_names_by_ids(session: AsyncSession, series_ids: Iterable[int]) -> dict[int, str]:
    """按漫剧主键一次取剧名，供别的业务包回填短剧名称。查不到或已软删的 id 不出现在结果里。"""
    pks = {int(series_id) for series_id in series_ids}
    if not pks:
        return {}
    rows = await session.execute(
        select(ManhuaSeries.id, ManhuaSeries.book_name).where(
            ManhuaSeries.id.in_(pks),
            ManhuaSeries.is_deleted == 0,
        )
    )
    return {int(series_id): book_name for series_id, book_name in rows.all()}


async def latest_create_time(session: AsyncSession) -> str:
    """未删除行里最晚的常读创建时间。没有则空串。"""
    result = await session.execute(
        select(func.max(ManhuaSeries.create_time)).where(
            ManhuaSeries.is_deleted == 0,
            ManhuaSeries.create_time != "",
        )
    )
    return result.scalar_one() or ""


async def insert_missing_series(
    session: AsyncSession,
    incoming: dict[tuple[int, str], dict[str, Any]],
) -> int:
    """表里已有同一 playlet_id + book_name 则跳过，只插入新行。返回插入条数。"""
    if not incoming:
        return 0
    result = await session.execute(
        select(ManhuaSeries.playlet_id, ManhuaSeries.book_name).where(
            tuple_(ManhuaSeries.playlet_id, ManhuaSeries.book_name).in_(list(incoming)),
            ManhuaSeries.is_deleted == 0,
        )
    )
    existing = {(playlet_id, book_name) for playlet_id, book_name in result.all()}
    now = beijing_now()
    inserted = 0
    for key, fields in incoming.items():
        if key in existing:
            continue
        fields["collected_at"] = now
        session.add(ManhuaSeries(**fields))
        inserted += 1
    return inserted
