"""投放读取三方剧场推广链。只查本模块的表。"""

from __future__ import annotations

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.envelope import ApiError
from app.modules.material.model import ManhuaSeries
from app.modules.theater.model import TheaterApp, TheaterPromotionLink

_CHARGE = {"IAA": ("IAA", 3), "IAP": ("IAP", 2)}


async def enabled_link(session: AsyncSession, series_id: int, charge: str) -> TheaterPromotionLink | None:
    """这部剧一条启用的 IAA 或 IAP 推广链。没有则空。"""
    name, media = _CHARGE[charge]
    result = await session.execute(
        select(TheaterPromotionLink)
        .where(
            TheaterPromotionLink.series_id == series_id,
            TheaterPromotionLink.is_deleted == 0,
            TheaterPromotionLink.is_enabled.is_(True),
            or_(
                TheaterPromotionLink.recharge_template_name == name,
                TheaterPromotionLink.media_config_type == media,
            ),
        )
        .order_by(TheaterPromotionLink.id.desc())
        .limit(1)
    )
    rows = result.scalars().all()
    return rows[0] if rows else None


async def require_link(session: AsyncSession, link_id: int, series_id: int) -> TheaterPromotionLink:
    """已投放的推广链必须属于这部剧。"""
    row = await session.get(TheaterPromotionLink, link_id)
    if row is None or row.is_deleted or int(row.series_id) != series_id:
        raise ApiError(400, "推广链不存在或不属于这部剧")
    return row


async def series_on_platform(
    session: AsyncSession, platform_id: int, *, iaa_only: bool
) -> list[tuple[ManhuaSeries, str]]:
    """平台下启用的推广链。每部剧只留一条链接。iaa_only 时只要免费墙。"""
    filters = [
        TheaterApp.platform_id == platform_id,
        TheaterApp.is_deleted == 0,
        TheaterPromotionLink.is_deleted == 0,
        TheaterPromotionLink.is_enabled.is_(True),
        ManhuaSeries.is_deleted == 0,
    ]
    if iaa_only:
        name, media = _CHARGE["IAA"]
        filters.append(
            or_(
                TheaterPromotionLink.recharge_template_name == name,
                TheaterPromotionLink.media_config_type == media,
            )
        )
    rows = (
        await session.execute(
            select(ManhuaSeries, TheaterPromotionLink.promotion_url)
            .join(TheaterPromotionLink, TheaterPromotionLink.series_id == ManhuaSeries.id)
            .join(TheaterApp, TheaterApp.id == TheaterPromotionLink.theater_app_id)
            .where(*filters)
            .order_by(ManhuaSeries.id, TheaterPromotionLink.id.desc())
        )
    ).all()
    picked: list[tuple[ManhuaSeries, str]] = []
    seen: set[int] = set()
    for series, url in rows:
        if int(series.id) in seen or not str(url or "").strip():
            continue
        seen.add(int(series.id))
        picked.append((series, str(url)))
    return picked
