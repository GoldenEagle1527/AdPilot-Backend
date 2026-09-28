"""三方剧场业务逻辑。平台和应用都是全员共用的配置，不做数据范围过滤。"""

from __future__ import annotations

from typing import Any

from sqlalchemy import ColumnElement
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.envelope import ApiError
from app.core.pagination import PageParams, page_data
from app.core.times import beijing_iso
from app.modules.theater.crud import app_name_taken, get_app, get_platform, page_apps, page_platforms
from app.modules.theater.model import TheaterApp, TheaterPlatform, TheaterType
from app.modules.theater.schema import AppCreate, AppQuery, AppStatusUpdate, PlatformQuery, PlatformUpdate

THEATER_TYPE_LABELS = {TheaterType.MINI_PROGRAM: "小程序", TheaterType.NATIVE: "端原生"}


def platform_item(row: TheaterPlatform) -> dict[str, Any]:
    """把平台行收成出参项。"""
    return {
        "id": str(row.id),
        "name": row.name,
        "code": row.code,
        "sort_order": row.sort_order,
        "is_enabled": row.is_enabled,
        "supports_mini_program": row.supports_mini_program,
        "supports_native": row.supports_native,
        "created_at": beijing_iso(row.created_date),
        "updated_at": beijing_iso(row.updated_date),
    }


def platform_filters(query: PlatformQuery) -> list[ColumnElement[bool]]:
    """拼列表过滤：恒限未删除；平台名称模糊且转义 % 和 _，启用状态精确匹配。"""
    filters: list[ColumnElement[bool]] = [TheaterPlatform.is_deleted == 0]
    name = (query.name or "").strip()
    if name:
        escaped = name.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        filters.append(TheaterPlatform.name.ilike(f"%{escaped}%", escape="\\"))
    if query.is_enabled is not None:
        filters.append(TheaterPlatform.is_enabled == query.is_enabled)
    return filters


async def list_platforms(session: AsyncSession, query: PlatformQuery) -> dict[str, Any]:
    """分页列出未删除的平台，按排序升序。"""
    params = PageParams(page=query.page, page_size=query.page_size)
    rows, total = await page_platforms(
        session, platform_filters(query), offset=params.offset, limit=params.page_size
    )
    return page_data([platform_item(row) for row in rows], total, params)


async def update_platform(
    session: AsyncSession, platform_id: int, body: PlatformUpdate
) -> dict[str, Any]:
    """只改传了的开关。改完重读一次，拿库里刷新后的更新时间。"""
    row = await get_platform(session, platform_id)
    if row is None:
        raise ApiError(404, "平台不存在")
    for field, value in body.model_dump(exclude_none=True).items():
        setattr(row, field, value)
    await session.commit()
    await session.refresh(row)
    return platform_item(row)


def app_item(row: TheaterApp, platform_name: str) -> dict[str, Any]:
    """把应用行收成出参项。"""
    return {
        "id": str(row.id),
        "platform_id": str(row.platform_id),
        "platform_name": platform_name,
        "name": row.name,
        "theater_type": row.theater_type,
        "delivery_mode": row.delivery_mode,
        "style": row.style,
        "ad_source": row.ad_source,
        "is_valid": row.is_valid,
        "created_at": beijing_iso(row.created_date),
        "updated_at": beijing_iso(row.updated_date),
    }


def app_filters(query: AppQuery) -> list[ColumnElement[bool]]:
    """拼列表过滤：恒限未删除；各筛选都精确匹配。"""
    filters: list[ColumnElement[bool]] = [TheaterApp.is_deleted == 0]
    if query.platform_id is not None:
        filters.append(TheaterApp.platform_id == query.platform_id)
    if query.theater_type is not None:
        filters.append(TheaterApp.theater_type == query.theater_type)
    if query.delivery_mode is not None:
        filters.append(TheaterApp.delivery_mode == query.delivery_mode)
    if query.style is not None:
        filters.append(TheaterApp.style == query.style)
    if query.is_valid is not None:
        filters.append(TheaterApp.is_valid == query.is_valid)
    return filters


async def list_apps(session: AsyncSession, query: AppQuery) -> dict[str, Any]:
    """分页列出未删除的应用，按创建时间倒序，带平台名称。"""
    params = PageParams(page=query.page, page_size=query.page_size)
    rows, total = await page_apps(session, app_filters(query), offset=params.offset, limit=params.page_size)
    return page_data([app_item(row, name) for row, name in rows], total, params)


async def usable_platform(session: AsyncSession, platform_id: int, theater_type: str) -> TheaterPlatform:
    """应用要挂的平台：须存在、已启用、且勾选了所选剧场类型。"""
    platform = await get_platform(session, platform_id)
    if platform is None:
        raise ApiError(404, "平台不存在")
    if not platform.is_enabled:
        raise ApiError(400, f"平台已禁用：{platform.name}")
    supported = (
        platform.supports_native if theater_type == TheaterType.NATIVE else platform.supports_mini_program
    )
    if not supported:
        raise ApiError(400, f"平台{platform.name}不支持{THEATER_TYPE_LABELS[TheaterType(theater_type)]}")
    return platform


async def require_free_name(session: AsyncSession, platform_id: int, name: str) -> None:
    """同平台下已有同名应用则 409。"""
    # ponytail: 先查后写，并发同名时靠唯一索引兜底，后到的那条会 500；真撞上再改成捕获 IntegrityError。
    if await app_name_taken(session, platform_id, name):
        raise ApiError(409, "剧场名称已存在")


async def create_app(session: AsyncSession, body: AppCreate) -> dict[str, Any]:
    """校验平台可用、同平台不重名后新增一条有效应用。"""
    platform = await usable_platform(session, body.platform_id, body.theater_type)
    await require_free_name(session, body.platform_id, body.name)
    row = TheaterApp(**body.model_dump(), is_valid=True)
    session.add(row)
    await session.commit()
    await session.refresh(row)
    return app_item(row, platform.name)


async def set_app_status(session: AsyncSession, app_id: int, body: AppStatusUpdate) -> dict[str, Any]:
    """只改应用状态，不验平台：平台已禁用时也能切换。"""
    row = await get_app(session, app_id)
    if row is None:
        raise ApiError(404, "应用不存在")
    row.is_valid = body.is_valid
    await session.commit()
    await session.refresh(row)
    platform = await get_platform(session, row.platform_id)
    return app_item(row, platform.name if platform else "")
