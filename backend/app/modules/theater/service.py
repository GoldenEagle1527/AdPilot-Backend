"""三方剧场业务逻辑。平台和应用都是全员共用的配置，不做数据范围过滤。"""

from __future__ import annotations

from datetime import datetime, time, timedelta
from typing import Any

from sqlalchemy import ColumnElement, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.envelope import ApiError
from app.core.pagination import PageParams, page_data
from app.core.times import BEIJING, beijing_iso, beijing_now
from app.modules.material.model import ManhuaSeries
from app.modules.theater.changdu import DELIVERY_MODE_BY_MEDIA, MEDIA_CONFIG_TYPES
from app.modules.theater.crud import (
    app_name_taken,
    close_open_tasks_for_series,
    existing_promotion_templates,
    existing_promotion_urls,
    first_app_by_delivery_mode,
    get_app,
    get_platform,
    get_promotion_link,
    get_series_for_update,
    page_apps,
    page_platforms,
    page_promotion_links,
    page_promotion_tasks,
    series_has_running_task,
)
from app.modules.theater.model import (
    DeliveryMode,
    PromotionLinkSource,
    PromotionTaskSource,
    PromotionTaskStatus,
    TheaterApp,
    TheaterPlatform,
    TheaterPromotionLink,
    TheaterPromotionTask,
    TheaterType,
)
from app.modules.theater.schema import (
    AppCreate,
    AppQuery,
    AppStatusUpdate,
    PlatformQuery,
    PlatformUpdate,
    PromotionCollectCreate,
    PromotionLinkCreate,
    PromotionLinkQuery,
    PromotionLinkUpdate,
    PromotionTaskQuery,
)

# 人工新增档位：入参字段 → 出价面板名；顺序即出参 items 顺序
MANUAL_LINK_TIERS: tuple[tuple[str, str, DeliveryMode], ...] = (
    ("iaa", "IAA", DeliveryMode.IAA),
    ("medium", "中额", DeliveryMode.IAP),
    ("small", "小额", DeliveryMode.IAP),
    ("extra_small", "超小额", DeliveryMode.IAP),
    ("ultra_small", "超超小额", DeliveryMode.IAP),
)

THEATER_TYPE_LABELS = {TheaterType.MINI_PROGRAM: "小程序", TheaterType.NATIVE: "端原生"}
# 列表只露开始执行之后的状态；pending 没到点、queued 排队中都不返回
VISIBLE_TASK_STATUSES = (
    PromotionTaskStatus.RUNNING,
    PromotionTaskStatus.SUCCESS,
    PromotionTaskStatus.FAILED,
)
SYSTEM_COLLECTOR = "系统"


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


def promotion_task_item(task: TheaterPromotionTask, series: ManhuaSeries, nickname: str | None) -> dict[str, Any]:
    """把任务行收成出参项。剧名、付费类型、短剧类型取短剧；没有采集人为系统。"""
    return {
        "id": str(task.id),
        "series_id": str(task.series_id),
        "book_name": series.book_name,
        "collector_name": nickname or SYSTEM_COLLECTOR,
        "tab_text": series.tab_text,
        "category_text": series.category_text,
        "status": task.status,
        "reason": task.reason,
        "execute_at": beijing_iso(task.execute_at),
        "finished_at": beijing_iso(task.finished_at) if task.finished_at else None,
    }


def promotion_task_filters(query: PromotionTaskQuery) -> list[ColumnElement[bool]]:
    """拼列表过滤：恒限未删除且只看三种可见状态；剧名模糊且转义 % 和 _，执行时间左闭右闭。"""
    filters: list[ColumnElement[bool]] = [
        TheaterPromotionTask.is_deleted == 0,
        TheaterPromotionTask.status.in_(VISIBLE_TASK_STATUSES),
    ]
    if query.status is not None:
        filters.append(TheaterPromotionTask.status == query.status)
    name = (query.book_name or "").strip()
    if name:
        escaped = name.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        filters.append(ManhuaSeries.book_name.ilike(f"%{escaped}%", escape="\\"))
    if query.execute_at_from is not None:
        filters.append(TheaterPromotionTask.execute_at >= query.execute_at_from)
    if query.execute_at_to is not None:
        filters.append(TheaterPromotionTask.execute_at <= query.execute_at_to)
    return filters


async def list_promotion_tasks(session: AsyncSession, query: PromotionTaskQuery) -> dict[str, Any]:
    """分页列出推广链同步任务，按执行时间倒序。"""
    params = PageParams(page=query.page, page_size=query.page_size)
    rows, total = await page_promotion_tasks(
        session, promotion_task_filters(query), offset=params.offset, limit=params.page_size
    )
    return page_data([promotion_task_item(*row) for row in rows], total, params)


# 表单「全部 / 付费 / 免费」落到任务上的过滤值。付费是常读 2，免费是常读 3。
_CHARGE_FILTER = {"all": "all", "paid": "IAP", "free": "IAA"}


async def create_manual_promotion_task(
    session: AsyncSession, body: PromotionCollectCreate, principal: dict[str, Any]
) -> dict[str, Any]:
    """写入一条来源为手动的初始任务。book_id 留在剧库，到执行时间再由任务去拉。"""
    found = await session.execute(
        select(ManhuaSeries).where(ManhuaSeries.id == body.series_id, ManhuaSeries.is_deleted == 0)
    )
    series = found.scalar_one_or_none()
    if series is None:
        raise ApiError(404, "短剧不存在")
    if not int(series.book_id or 0):
        raise ApiError(400, "短剧没有 book_id")
    nickname = str(principal.get("nickname") or "").strip() or SYSTEM_COLLECTOR
    row = TheaterPromotionTask(
        series_id=series.id,
        collector_id=int(principal["id"]),
        source=PromotionTaskSource.MANUAL,
        status=PromotionTaskStatus.PENDING,
        reason="",
        execute_at=body.execute_at,
        finished_at=None,
        retry_count=0,
        charge_filter=_CHARGE_FILTER[body.charge_type],
    )
    session.add(row)
    await session.commit()
    await session.refresh(row)
    return {
        "id": str(row.id),
        "series_id": str(series.id),
        "book_name": series.book_name,
        "collector_name": nickname,
        "charge_type": body.charge_type,
        "status": row.status,
        "execute_at": beijing_iso(row.execute_at),
    }


def promotion_link_item(link: TheaterPromotionLink, book_name: str, app_name: str | None) -> dict[str, Any]:
    """把推广链行收成出参项。剧名取剧库，剧场名取应用；对应不上剧场为 null。"""
    return {
        "id": str(link.id),
        "theater_app_id": str(link.theater_app_id) if link.theater_app_id else None,
        "theater_app_name": app_name,
        "series_id": str(link.series_id),
        "book_name": book_name,
        "is_enabled": link.is_enabled,
        "recharge_template_name": link.recharge_template_name,
        "publish_time": beijing_iso(link.publish_time) if link.publish_time else None,
        "promotion_url": link.promotion_url,
        "promotion_create_time": beijing_iso(link.promotion_create_time) if link.promotion_create_time else None,
    }


def promotion_link_filters(query: PromotionLinkQuery) -> list[ColumnElement[bool]]:
    """拼列表过滤：恒限未删除；首发日期按北京自然日左闭右闭，其余精确匹配。"""
    filters: list[ColumnElement[bool]] = [TheaterPromotionLink.is_deleted == 0]
    if query.publish_date_from is not None:
        start = datetime.combine(query.publish_date_from, time.min, tzinfo=BEIJING)
        filters.append(TheaterPromotionLink.publish_time >= start)
    if query.publish_date_to is not None:
        end = datetime.combine(query.publish_date_to + timedelta(days=1), time.min, tzinfo=BEIJING)
        filters.append(TheaterPromotionLink.publish_time < end)
    if query.theater_app_id is not None:
        filters.append(TheaterPromotionLink.theater_app_id == query.theater_app_id)
    if query.series_id is not None:
        filters.append(TheaterPromotionLink.series_id == query.series_id)
    if query.is_enabled is not None:
        filters.append(TheaterPromotionLink.is_enabled == query.is_enabled)
    return filters


async def list_promotion_links(session: AsyncSession, query: PromotionLinkQuery) -> dict[str, Any]:
    """分页列出端原生推广链，按创建时间倒序。"""
    params = PageParams(page=query.page, page_size=query.page_size)
    rows, total = await page_promotion_links(
        session, promotion_link_filters(query), offset=params.offset, limit=params.page_size
    )
    return page_data([promotion_link_item(*row) for row in rows], total, params)


async def create_promotion_links(session: AsyncSession, body: PromotionLinkCreate) -> dict[str, Any]:
    """按档位批量人工新增。剧场按 IAA/IAP 各取第一条有效应用；锁短剧；同步中拒绝；同剧同 URL/档位跳过。

    写成功后关掉同剧 pending/queued 任务，避免定时稍后又落一遍。
    """
    series = await get_series_for_update(session, body.series_id)
    if series is None:
        raise ApiError(404, "短剧不存在")
    if await series_has_running_task(session, series.id):
        raise ApiError(409, "该短剧正在同步推广链，请稍后再试")
    apps = {
        DeliveryMode.IAA: await first_app_by_delivery_mode(session, DeliveryMode.IAA),
        DeliveryMode.IAP: await first_app_by_delivery_mode(session, DeliveryMode.IAP),
    }
    seen_urls = await existing_promotion_urls(session, series.id)
    seen_templates = await existing_promotion_templates(session, series.id)
    now = beijing_now()
    rows: list[TheaterPromotionLink] = []
    for field, template, mode in MANUAL_LINK_TIERS:
        url = getattr(body, field)
        if not url or url in seen_urls or template in seen_templates:
            continue
        seen_urls.add(url)
        seen_templates.add(template)
        app = apps[mode]
        rows.append(
            TheaterPromotionLink(
                theater_app_id=app.id if app else None,
                series_id=series.id,
                source=PromotionLinkSource.MANUAL,
                promotion_url=url,
                recharge_template_name=template,
                media_config_type=MEDIA_CONFIG_TYPES[mode],
                publish_time=series.estimate_publish_time,
                promotion_create_time=now,
                is_enabled=True,
            )
        )
    if not rows:
        raise ApiError(409, "推广链已存在")
    session.add_all(rows)
    await close_open_tasks_for_series(session, series.id, reason="已人工新增推广链", finished_at=now)
    await session.commit()
    for row in rows:
        await session.refresh(row)
    app_names = {mode: (app.name if app else None) for mode, app in apps.items()}
    return {
        "items": [
            promotion_link_item(
                row,
                series.book_name,
                app_names.get(mode) if (mode := DELIVERY_MODE_BY_MEDIA.get(row.media_config_type)) else None,
            )
            for row in rows
        ]
    }


async def update_promotion_link(session: AsyncSession, link_id: int, body: PromotionLinkUpdate) -> dict[str, Any]:
    """只改传了的字段，剧名不可改。换剧场时剧场须存在。"""
    link = await get_promotion_link(session, link_id)
    if link is None:
        raise ApiError(404, "推广链不存在")
    changes = body.model_dump(exclude_unset=True)
    app = None
    if changes.get("theater_app_id") is not None:
        app = await get_app(session, changes["theater_app_id"])
        if app is None:
            raise ApiError(404, "剧场不存在")
    for field, value in changes.items():
        setattr(link, field, value)
    await session.commit()
    await session.refresh(link)
    if app is None and link.theater_app_id is not None:
        app = await get_app(session, link.theater_app_id)
    series = await session.get(ManhuaSeries, link.series_id)
    return promotion_link_item(link, series.book_name if series else "", app.name if app else None)
