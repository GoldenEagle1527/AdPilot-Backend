"""三方剧场表查询。"""

from __future__ import annotations

from sqlalchemy import ColumnElement, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.theater.model import TheaterApp, TheaterPlatform


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
