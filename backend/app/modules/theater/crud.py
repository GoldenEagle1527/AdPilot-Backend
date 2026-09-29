"""三方剧场表查询。"""

from __future__ import annotations

from collections.abc import Iterable
from datetime import datetime
from typing import Any

from sqlalchemy import ColumnElement, false, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.material.model import ManhuaSeries
from app.modules.system_admin.domain.models import User
from app.modules.theater.model import (
    PromotionTaskStatus,
    TheaterApp,
    TheaterPlatform,
    TheaterPromotionLink,
    TheaterPromotionTask,
)


async def page_platforms(
    session: AsyncSession,
    filters: list[ColumnElement[bool]],
    *,
    offset: int,
    limit: int,
) -> tuple[list[TheaterPlatform], int]:
    """按排序升序、同序按 id 升序分页平台。返回 (行, 总数)。"""
    total = int(
        (
            await session.execute(select(func.count()).select_from(TheaterPlatform).where(*filters))
        ).scalar_one()
    )
    result = await session.execute(
        select(TheaterPlatform)
        .where(*filters)
        .order_by(TheaterPlatform.sort_order, TheaterPlatform.id)
        .offset(offset)
        .limit(limit)
    )
    return list(result.scalars().all()), total


async def get_platform(session: AsyncSession, platform_id: int) -> TheaterPlatform | None:
    """取一条未删除的平台。"""
    result = await session.execute(
        select(TheaterPlatform).where(TheaterPlatform.id == platform_id, TheaterPlatform.is_deleted == 0)
    )
    return result.scalar_one_or_none()


async def page_apps(
    session: AsyncSession,
    filters: list[ColumnElement[bool]],
    *,
    offset: int,
    limit: int,
) -> tuple[list[tuple[TheaterApp, str]], int]:
    """按创建时间倒序、同秒按 id 倒序分页应用，连带平台名称。返回 ([(应用, 平台名称)], 总数)。"""
    total = int(
        (await session.execute(select(func.count()).select_from(TheaterApp).where(*filters))).scalar_one()
    )
    result = await session.execute(
        select(TheaterApp, TheaterPlatform.name)
        .join(TheaterPlatform, TheaterPlatform.id == TheaterApp.platform_id)
        .where(*filters)
        .order_by(TheaterApp.created_date.desc(), TheaterApp.id.desc())
        .offset(offset)
        .limit(limit)
    )
    return [(row, name) for row, name in result.all()], total


async def get_app(session: AsyncSession, app_id: int) -> TheaterApp | None:
    """取一条未删除的应用。"""
    result = await session.execute(
        select(TheaterApp).where(TheaterApp.id == app_id, TheaterApp.is_deleted == 0)
    )
    return result.scalar_one_or_none()


async def app_name_taken(session: AsyncSession, platform_id: int, name: str) -> bool:
    """同平台下是否已有未删除的同名应用。"""
    result = await session.execute(
        select(TheaterApp.id)
        .where(TheaterApp.platform_id == platform_id, TheaterApp.name == name, TheaterApp.is_deleted == 0)
        .limit(1)
    )
    return result.scalar_one_or_none() is not None


async def page_promotion_tasks(
    session: AsyncSession,
    filters: list[ColumnElement[bool]],
    *,
    offset: int,
    limit: int,
) -> tuple[list[tuple[TheaterPromotionTask, ManhuaSeries, str | None]], int]:
    """按执行时间倒序、同秒按 id 倒序分页任务，连带短剧和采集人昵称。返回 ([(任务, 短剧, 昵称)], 总数)。"""
    total = int(
        (
            await session.execute(
                select(func.count())
                .select_from(TheaterPromotionTask)
                .join(ManhuaSeries, ManhuaSeries.id == TheaterPromotionTask.series_id)
                .where(*filters)
            )
        ).scalar_one()
    )
    result = await session.execute(
        select(TheaterPromotionTask, ManhuaSeries, User.nickname)
        .join(ManhuaSeries, ManhuaSeries.id == TheaterPromotionTask.series_id)
        .outerjoin(User, User.id == TheaterPromotionTask.collector_id)
        .where(*filters)
        .order_by(TheaterPromotionTask.execute_at.desc(), TheaterPromotionTask.id.desc())
        .offset(offset)
        .limit(limit)
    )
    return [(task, series, nickname) for task, series, nickname in result.all()], total


async def page_promotion_links(
    session: AsyncSession,
    filters: list[ColumnElement[bool]],
    *,
    offset: int,
    limit: int,
) -> tuple[list[tuple[TheaterPromotionLink, str, str | None]], int]:
    """按创建时间倒序、同秒按 id 倒序分页推广链，连带剧名和剧场名称。返回 ([(推广链, 剧名, 剧场名)], 总数)。"""
    total = int(
        (
            await session.execute(select(func.count()).select_from(TheaterPromotionLink).where(*filters))
        ).scalar_one()
    )
    result = await session.execute(
        select(TheaterPromotionLink, ManhuaSeries.book_name, TheaterApp.name)
        .join(ManhuaSeries, ManhuaSeries.id == TheaterPromotionLink.series_id)
        .outerjoin(TheaterApp, TheaterApp.id == TheaterPromotionLink.theater_app_id)
        .where(*filters)
        .order_by(TheaterPromotionLink.created_date.desc(), TheaterPromotionLink.id.desc())
        .offset(offset)
        .limit(limit)
    )
    return [(link, book_name, app_name) for link, book_name, app_name in result.all()], total


async def get_promotion_link(session: AsyncSession, link_id: int) -> TheaterPromotionLink | None:
    """取一条未删除的推广链。"""
    result = await session.execute(
        select(TheaterPromotionLink).where(TheaterPromotionLink.id == link_id, TheaterPromotionLink.is_deleted == 0)
    )
    return result.scalar_one_or_none()


async def create_due_auto_tasks(session: AsyncSession, now: datetime) -> list[int]:
    """到预估投放时间且没触发过的短剧，打上已触发并各建一条自动任务。返回这批短剧 id。

    单条 UPDATE ... RETURNING：并发执行时后到的会重新判断 promotion_triggered，同一部剧只建一条。
    条件必须写 = false、不能写 IS false，否则对不上部分索引 ix_manhua_series_promotion_pending，会全表扫。
    """
    result = await session.execute(
        update(ManhuaSeries)
        .where(
            ManhuaSeries.promotion_triggered == false(),
            ManhuaSeries.is_deleted == 0,
            ManhuaSeries.estimate_publish_time <= now,
        )
        .values(promotion_triggered=True)
        .returning(ManhuaSeries.id)
        .execution_options(synchronize_session=False)
    )
    series_ids = list(result.scalars().all())
    session.add_all(TheaterPromotionTask(series_id=series_id, execute_at=now) for series_id in series_ids)
    return series_ids


async def claim_due_tasks(session: AsyncSession, now: datetime, limit: int) -> list[int]:
    """按执行时间先后领最多 limit 条到点的初始任务，改成爬虫处理中并取回 id。

    SKIP LOCKED：两次执行撞上时各领各的，不互相等，同一条也只会被领一次。
    """
    due = (
        select(TheaterPromotionTask.id)
        .where(
            TheaterPromotionTask.status == PromotionTaskStatus.PENDING,
            TheaterPromotionTask.is_deleted == 0,
            TheaterPromotionTask.execute_at <= now,
        )
        .order_by(TheaterPromotionTask.execute_at, TheaterPromotionTask.id)
        .limit(limit)
        .with_for_update(skip_locked=True)
    )
    result = await session.execute(
        update(TheaterPromotionTask)
        .where(TheaterPromotionTask.id.in_(due.scalar_subquery()))
        .values(status=PromotionTaskStatus.RUNNING)
        .returning(TheaterPromotionTask.id)
        .execution_options(synchronize_session=False)
    )
    return list(result.scalars().all())


async def get_task_with_series(
    session: AsyncSession, task_id: int
) -> tuple[TheaterPromotionTask, ManhuaSeries] | None:
    """取一条未删除任务和它的短剧。"""
    result = await session.execute(
        select(TheaterPromotionTask, ManhuaSeries)
        .join(ManhuaSeries, ManhuaSeries.id == TheaterPromotionTask.series_id)
        .where(TheaterPromotionTask.id == task_id, TheaterPromotionTask.is_deleted == 0)
    )
    row = result.first()
    return (row[0], row[1]) if row else None


async def insert_missing_links(session: AsyncSession, links: Iterable[dict[str, Any]]) -> int:
    """按常读 promotion_id 去重插入推广链，表里已有的跳过不覆盖（保住人工编辑）。返回插入条数。"""
    incoming = {link["promotion_id"]: link for link in links}
    if not incoming:
        return 0
    result = await session.execute(
        select(TheaterPromotionLink.promotion_id).where(TheaterPromotionLink.promotion_id.in_(list(incoming)))
    )
    existing = set(result.scalars().all())
    fresh = [link for promotion_id, link in incoming.items() if promotion_id not in existing]
    session.add_all(TheaterPromotionLink(**link) for link in fresh)
    return len(fresh)
