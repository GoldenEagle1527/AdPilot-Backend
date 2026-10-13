"""投放读取三方剧场推广链。只查本模块的表。"""

from __future__ import annotations

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import Select

from app.core.envelope import ApiError
from app.modules.material.model import ManhuaSeries
from app.modules.theater.model import TheaterApp, TheaterPromotionLink

_CHARGE = {"IAA": ("IAA", 3), "IAP": ("IAP", 2)}
_TIER_ORDER = ("IAA", "中额", "小额", "超小额", "超超小额")


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


def link_charge_mode(name: str, media_config_type: int) -> str:
    """档位名是 IAA，或付费墙类型是免费，记 IAA。中额等以及其余付费记 IAP。"""
    if name == "IAA" or int(media_config_type) == _CHARGE["IAA"][1]:
        return "IAA"
    return "IAP"


def _tier_rank(name: str) -> int:
    """已知档位按固定顺序，其余名字排在后面。"""
    try:
        return _TIER_ORDER.index(name)
    except ValueError:
        return len(_TIER_ORDER)


def enabled_series_links_stmt(series_id: int) -> Select[tuple[TheaterPromotionLink]]:
    """这部剧启用且未删除、链接正文不是空串的推广链。"""
    return select(TheaterPromotionLink).where(
        TheaterPromotionLink.series_id == series_id,
        TheaterPromotionLink.is_deleted == 0,
        TheaterPromotionLink.is_enabled.is_(True),
        TheaterPromotionLink.promotion_url != "",
    )


async def enabled_series_links(session: AsyncSession, series_id: int) -> list[TheaterPromotionLink]:
    """全部带出。同一档位多条都留。顺序是 IAA、中额、小额、超小额、超超小额，其余在后。"""
    result = await session.execute(enabled_series_links_stmt(series_id))
    rows = [
        row
        for row in result.scalars().all()
        if not row.is_deleted and row.is_enabled and str(row.promotion_url or "").strip()
    ]
    rows.sort(key=lambda row: (_tier_rank(str(row.recharge_template_name or "")), int(row.id or 0)))
    return rows


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
