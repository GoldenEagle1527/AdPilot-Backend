"""列表只读日表。剧目、项目、计划把区间内的日行相加；全域按日期直接取出。"""

from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.report.fold import fold_manhua_dramas, fold_manhua_projects, fold_manhua_promotions, uni_row_metrics
from app.modules.report.schema import ManhuaQuery, UniQuery
from app.modules.report.serving import (
    ReportManhuaDramaDay,
    ReportManhuaProjectDay,
    ReportManhuaPromotionDay,
    ReportUniDramaDay,
    ReportUniGroupDay,
    ReportUniPitcherDay,
    ReportUniPitcherDramaDay,
)

_DRAMA_FIELDS = (
    "series_id",
    "panel_key",
    "book_name",
    "drama_type",
    "channel",
    "publish_date",
    "pitcher_ids",
    "pitcher_names",
    "department_names",
    "bid_types",
    "panel_names",
    "costed_promotion_ids",
    "stat_cost",
    "stat_pay_amount",
    "attribution_game_in_app_ltv_1day",
    "attribution_game_in_app_ltv_8days",
    "attribution_micro_game_0d_ltv",
    "attribution_micro_game_7d_ltv",
    "show_cnt",
    "click_cnt",
    "convert_cnt",
    "active",
)
_OWNED_FIELDS = (
    "project_id",
    "project_name",
    "series_id",
    "book_name",
    "pitcher_id",
    "pitcher_name",
    "department_name",
    "bid_type",
    "drama_type",
    "channel",
    "panel",
    "publish_date",
    "created_at",
    "first_cost_time",
    "project_budget",
    "roi_goal",
    "stat_cost",
    "stat_pay_amount",
    "attribution_game_in_app_ltv_1day",
    "attribution_game_in_app_ltv_8days",
    "attribution_micro_game_0d_ltv",
    "attribution_micro_game_7d_ltv",
    "show_cnt",
    "click_cnt",
    "convert_cnt",
    "active",
)


def _pack(row: Any, names: tuple[str, ...]) -> dict[str, Any]:
    return {name: getattr(row, name) for name in names}


async def manhua_drama_rows(session: AsyncSession, query: ManhuaQuery, user_id: int | None) -> list[dict[str, Any]]:
    rows = await session.execute(
        select(ReportManhuaDramaDay).where(
            ReportManhuaDramaDay.is_deleted == 0,
            ReportManhuaDramaDay.charge_mode == query.charge_mode,
            ReportManhuaDramaDay.stat_date >= query.date_start,
            ReportManhuaDramaDay.stat_date <= query.date_end,
        )
    )
    return fold_manhua_dramas([_pack(row, _DRAMA_FIELDS) for row in rows.scalars()], query, user_id)


async def manhua_project_rows(session: AsyncSession, query: ManhuaQuery, user_id: int | None) -> list[dict[str, Any]]:
    filters = [
        ReportManhuaProjectDay.is_deleted == 0,
        ReportManhuaProjectDay.charge_mode == query.charge_mode,
        ReportManhuaProjectDay.stat_date >= query.date_start,
        ReportManhuaProjectDay.stat_date <= query.date_end,
    ]
    if user_id is not None:
        filters.append(ReportManhuaProjectDay.pitcher_id == user_id)
    rows = await session.execute(select(ReportManhuaProjectDay).where(*filters))
    return fold_manhua_projects([_pack(row, _OWNED_FIELDS) for row in rows.scalars()], query, user_id)


async def manhua_promotion_rows(session: AsyncSession, query: ManhuaQuery, user_id: int | None) -> list[dict[str, Any]]:
    names = ("promotion_id", "promotion_name", *_OWNED_FIELDS)
    filters = [
        ReportManhuaPromotionDay.is_deleted == 0,
        ReportManhuaPromotionDay.charge_mode == query.charge_mode,
        ReportManhuaPromotionDay.stat_date >= query.date_start,
        ReportManhuaPromotionDay.stat_date <= query.date_end,
    ]
    if user_id is not None:
        filters.append(ReportManhuaPromotionDay.pitcher_id == user_id)
    rows = await session.execute(select(ReportManhuaPromotionDay).where(*filters))
    return fold_manhua_promotions([_pack(row, names) for row in rows.scalars()], query, user_id)


async def uni_drama_rows(session: AsyncSession, query: UniQuery, user_id: int | None) -> list[dict[str, Any]]:
    filters = [
        ReportUniDramaDay.is_deleted == 0,
        ReportUniDramaDay.stat_date >= query.date_start,
        ReportUniDramaDay.stat_date <= query.date_end,
    ]
    if user_id is not None:
        filters.append(ReportUniDramaDay.pitcher_ids.contains([user_id]))
    stmt = select(ReportUniDramaDay).where(*filters)
    if query.series_name:
        stmt = stmt.where(ReportUniDramaDay.book_name.contains(query.series_name.strip()))
    rows = await session.execute(stmt)
    return [_uni_drama(_pack_uni(row)) for row in rows.scalars()]


async def uni_pitcher_drama_rows(session: AsyncSession, query: UniQuery, user_id: int | None) -> list[dict[str, Any]]:
    filters = [
        ReportUniPitcherDramaDay.is_deleted == 0,
        ReportUniPitcherDramaDay.stat_date >= query.date_start,
        ReportUniPitcherDramaDay.stat_date <= query.date_end,
    ]
    if user_id is not None:
        filters.append(ReportUniPitcherDramaDay.pitcher_id == user_id)
    stmt = select(ReportUniPitcherDramaDay).where(*filters)
    if query.series_name:
        stmt = stmt.where(ReportUniPitcherDramaDay.book_name.contains(query.series_name.strip()))
    rows = await session.execute(stmt)
    packed = []
    for row in rows.scalars():
        item = _uni_drama(_pack_uni(row))
        item["pitcher_user_id"] = row.pitcher_id
        item["pitcher_name"] = row.pitcher_name
        packed.append(item)
    return packed


async def uni_pitcher_rows(session: AsyncSession, query: UniQuery, user_id: int | None) -> list[dict[str, Any]]:
    filters = [
        ReportUniPitcherDay.is_deleted == 0,
        ReportUniPitcherDay.stat_date >= query.date_start,
        ReportUniPitcherDay.stat_date <= query.date_end,
    ]
    if user_id is not None:
        filters.append(ReportUniPitcherDay.pitcher_id == user_id)
    rows = await session.execute(select(ReportUniPitcherDay).where(*filters))
    out = []
    for row in rows.scalars():
        item = uni_row_metrics(_pack_uni(row))
        item.update(
            pitcher_user_id=row.pitcher_id,
            pitcher_name=row.pitcher_name,
            stat_time_day=row.stat_date.isoformat(),
            new_drama_count=0,
        )
        out.append(item)
    return out


async def uni_group_rows(
    session: AsyncSession, query: UniQuery, department_ids: set[int] | None
) -> list[dict[str, Any]]:
    """department_ids 为空表示全部部门。空集合表示没有可见部门。"""
    filters = [
        ReportUniGroupDay.is_deleted == 0,
        ReportUniGroupDay.stat_date >= query.date_start,
        ReportUniGroupDay.stat_date <= query.date_end,
    ]
    if department_ids is not None:
        if not department_ids:
            return []
        filters.append(ReportUniGroupDay.department_id.in_(department_ids))
    rows = await session.execute(select(ReportUniGroupDay).where(*filters))
    out = []
    for row in rows.scalars():
        item = uni_row_metrics(_pack_uni(row))
        item.update(
            department_id=row.department_id,
            department_name=row.department_name,
            stat_time_day=row.stat_date.isoformat(),
            new_drama_count=0,
        )
        out.append(item)
    return out


def _pack_uni(row: Any) -> dict[str, Any]:
    return {
        "series_id": getattr(row, "series_id", None),
        "book_name": getattr(row, "book_name", ""),
        "platform_name": getattr(row, "platform_name", ""),
        "stat_date": row.stat_date,
        "all_stat_cost_trend": row.all_stat_cost_trend,
        "all_stat_total_cost_trend": row.all_stat_total_cost_trend,
        "all_gmv_trend": row.all_gmv_trend,
        "all_billing_gmv_0day_trend": row.all_billing_gmv_0day_trend,
        "all_billing_gmv_24h_trend": row.all_billing_gmv_24h_trend,
        "all_billing_gmv_3days_trend": row.all_billing_gmv_3days_trend,
        "all_income_trend": row.all_income_trend,
        "all_income_0day_trend": row.all_income_0day_trend,
        "all_pay_amount_income_trend": row.all_pay_amount_income_trend,
        "all_micro_game_income_trend": row.all_micro_game_income_trend,
        "new_project_count": row.new_project_count,
    }


def _uni_drama(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "series_id": row["series_id"],
        "book_name": row["book_name"] or "",
        "platform_name": row["platform_name"] or "",
        "stat_time_day": row["stat_date"].isoformat(),
        **uni_row_metrics(row),
    }
