"""草稿和自动规则共用的账户、视频、标题和推广链匹配。"""

from __future__ import annotations

import random
from datetime import date, datetime, time, timedelta
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.envelope import ApiError
from app.core.times import BEIJING
from app.modules.account.model import AdvertiserAccount, OeProject, OePromotion, OeReportSnapshot, ProductLibrary
from app.modules.material.model import ManhuaSeries
from app.modules.material_title.model import MaterialTitle
from app.modules.material_video.model import MaterialVideo
from app.modules.material_video.schema import VideoQuery
from app.modules.material_video.service import video_filters
from app.modules.standard_delivery.crud import get_library_by_id
from app.modules.theater.model import TheaterPromotionLink

_TITLE_MIN = 5
_TITLE_MAX = 55


def rule_display_name(kind: str, when: datetime) -> str:
    """按文档生成规则名。时间用北京时间到秒。"""
    clock = when if when.tzinfo is not None else when.replace(tzinfo=BEIJING)
    stamp = clock.astimezone(BEIJING).strftime("%Y%m%d%H%M%S")
    if kind == "cost":
        return f"IAA端原生短剧消耗自动批量-{stamp}"
    return f"IAA端原生自动批量-{stamp}"


def series_link_names(book_name: str) -> tuple[str, str]:
    """短剧简称取前两字，推广链接名称是原生-加前两字。"""
    short = (book_name or "")[:2]
    return short, f"原生-{short}"


async def match_advertisers(
    session: AsyncSession, user_id: int, limit: int, *, unused_only: bool
) -> list[AdvertiserAccount]:
    """当前投手的账户。自动规则要还没建过项目的新账户，不按 id 从小到大取前几个。"""
    stmt = select(AdvertiserAccount).where(
        AdvertiserAccount.pitcher_user_id == user_id,
        AdvertiserAccount.is_deleted == 0,
        AdvertiserAccount.sync_status == "active",
    )
    if unused_only:
        used = select(OeProject.advertiser_id).where(OeProject.is_deleted == 0)
        stmt = stmt.where(AdvertiserAccount.advertiser_id.not_in(used))
    rows = await session.scalars(
        stmt.order_by(AdvertiserAccount.assigned_at.desc().nulls_last(), AdvertiserAccount.id.desc()).limit(limit)
    )
    return list(rows.all())


async def series_videos(
    session: AsyncSession, series_id: int, user_id: int, *, limit: int, order: str
) -> list[MaterialVideo]:
    """从这部剧的素材库代入。upload 按上传顺序，random 打乱。"""
    rows = await session.scalars(
        select(MaterialVideo)
        .where(*video_filters(VideoQuery(series_id=series_id), user_id))
        .order_by(MaterialVideo.created_date, MaterialVideo.id)
        .limit(limit)
    )
    picked = list(rows.all())
    if order == "random":
        random.shuffle(picked)
    return picked


async def library_titles(
    session: AsyncSession, user_id: int, *, limit: int, category: str | None
) -> list[MaterialTitle]:
    """自动选择时从标题库带入。长度按 5–55 个字。"""
    filters = [MaterialTitle.uploader_id == user_id, MaterialTitle.is_deleted == 0]
    if category:
        filters.append(MaterialTitle.category == category)
    rows = await session.scalars(
        select(MaterialTitle).where(*filters).order_by(MaterialTitle.id).limit(200)
    )
    picked = [row for row in rows.all() if _TITLE_MIN <= len(row.title) <= _TITLE_MAX]
    return picked[:limit]


async def iaa_link_for_series(session: AsyncSession, series_id: int) -> TheaterPromotionLink | None:
    """这部剧一条启用的 IAA 推广链。"""
    row = await session.scalar(
        select(TheaterPromotionLink)
        .where(
            TheaterPromotionLink.series_id == series_id,
            TheaterPromotionLink.is_deleted == 0,
            TheaterPromotionLink.is_enabled.is_(True),
            (TheaterPromotionLink.recharge_template_name == "IAA")
            | (TheaterPromotionLink.media_config_type == 3),
        )
        .order_by(TheaterPromotionLink.id.desc())
        .limit(1)
    )
    return row


async def promotion_link_by_id(
    session: AsyncSession, link_id: int, series_id: int
) -> TheaterPromotionLink:
    """已投放的推广链必须属于这部剧。"""
    row = await session.get(TheaterPromotionLink, link_id)
    if row is None or row.is_deleted or int(row.series_id) != series_id:
        raise ApiError(400, "推广链不存在或不属于这部剧")
    return row


async def other_series_name(session: AsyncSession, series_id: int) -> str:
    """非本剧商品用另一部剧的剧名。"""
    row = await session.get(ManhuaSeries, series_id)
    if row is None or row.is_deleted:
        raise ApiError(404, "短剧不存在")
    return str(row.book_name)


async def bound_library(session: AsyncSession, library_id: int) -> ProductLibrary:
    """模板上绑定的那一条商品库。"""
    library = await get_library_by_id(session, library_id)
    if library is None:
        raise ApiError(404, "商品库不存在")
    return library


def _belongs_to_series(raw: object, promo_name: str | None, series_id: int, book_name: str) -> bool:
    """快照要能对上这部剧，不能拿全库任意一行。"""
    if isinstance(raw, dict):
        if str(raw.get("series_id") or "") == str(series_id):
            return True
        if str(raw.get("book_name") or "") == book_name:
            return True
    text = str(promo_name or "")
    return bool(book_name) and book_name in text


async def series_stats(
    session: AsyncSession,
    series_id: int,
    book_name: str,
    day: date | None = None,
) -> list[tuple[Decimal, Decimal]]:
    """这部剧在某一天（或全部）的消耗和回收比值。"""
    stmt = (
        select(
            OeReportSnapshot.stat_cost,
            OeReportSnapshot.attribution_micro_game_0d_roi,
            OeReportSnapshot.raw_payload,
            OePromotion.name,
        )
        .outerjoin(
            OePromotion,
            (OePromotion.promotion_id == OeReportSnapshot.promotion_id)
            & (OePromotion.is_deleted == 0),
        )
        .where(OeReportSnapshot.is_deleted == 0)
    )
    if day is not None:
        start = datetime.combine(day, time.min, tzinfo=BEIJING)
        stmt = stmt.where(
            OeReportSnapshot.synced_at >= start,
            OeReportSnapshot.synced_at < start + timedelta(days=1),
        )
    rows = (await session.execute(stmt)).all()
    picked: list[tuple[Decimal, Decimal]] = []
    for cost, roi, raw, promo_name in rows:
        if _belongs_to_series(raw, promo_name, series_id, book_name):
            picked.append((Decimal(cost), Decimal(roi)))
    return picked
