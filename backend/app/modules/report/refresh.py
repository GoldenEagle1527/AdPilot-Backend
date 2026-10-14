"""用原始小时快照和中台归属，刷接口日表。列表不再做这件事。"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import delete, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.report import crud
from app.modules.report.ledger_store import replace_ledger_days
from app.modules.report.schema import ManhuaQuery
from app.modules.report.service import (
    MANHUA_BASE,
    UNI_MONEY,
    manhua_drama_rows,
    manhua_project_rows,
    manhua_promotion_rows,
    uni_drama_rows,
    uni_group_rows,
    uni_pitcher_rows,
)
from app.modules.report.serving import (
    ReportManhuaDramaDay,
    ReportManhuaProjectDay,
    ReportManhuaPromotionDay,
    ReportUniDramaDay,
    ReportUniGroupDay,
    ReportUniPitcherDay,
    ReportUniPitcherDramaDay,
)

_MANHUA_TABLES = (ReportManhuaDramaDay, ReportManhuaProjectDay, ReportManhuaPromotionDay)
_UNI_TABLES = (ReportUniDramaDay, ReportUniPitcherDramaDay, ReportUniPitcherDay, ReportUniGroupDay)


async def rebuild_serving(session: AsyncSession, days: list[date]) -> int:
    """删掉这些统计日的日表，再按原始快照重写。返回写入行数。"""
    if not days:
        return 0
    for model in (*_MANHUA_TABLES, *_UNI_TABLES):
        await session.execute(delete(model).where(model.stat_date.in_(days)))
    written = 0
    for day in days:
        for mode in ("IAP", "IAA"):
            written += await _manhua_day(session, day, mode)
        written += await _uni_day(session, day)
    written += await replace_ledger_days(session, days)
    await session.commit()
    return written


async def _manhua_day(session: AsyncSession, day: date, mode: str) -> int:
    facts = await crud.manhua_facts(session, day, day, mode)
    project_ids = {fact.project_id for fact in facts}
    promotion_ids = {fact.promotion_id for fact in facts}
    links = await crud.standard_links(session, charge_mode=mode, project_ids=project_ids)
    promotions = await crud.standard_promotions(session, promotion_ids)
    project_first = await crud.manhua_first_cost(session, project_ids, by_promotion=False)
    promotion_first = await crud.manhua_first_cost(session, promotion_ids, by_promotion=True)
    query = ManhuaQuery(charge_mode=mode, date_start=day, date_end=day)
    dramas = manhua_drama_rows(facts, links, query, None)
    projects = manhua_project_rows(facts, links, query, None, project_first)
    ads = manhua_promotion_rows(facts, links, promotions, query, None, promotion_first)
    for row in dramas:
        session.add(_drama(day, mode, row))
    for row in projects:
        session.add(_project(day, mode, row))
    for row in ads:
        session.add(_promotion(day, mode, row))
    return len(dramas) + len(projects) + len(ads)


async def _uni_day(session: AsyncSession, day: date) -> int:
    facts = await crud.uni_facts(session, day, day)
    links = await crud.uni_links(
        session,
        project_ids={fact.project_id for fact in facts},
        created_between=(day, day),
    )
    dramas = uni_drama_rows(facts, links, day, day, None)
    pitcher_dramas = uni_drama_rows(facts, links, day, day, None, by_pitcher=True)
    pitchers = uni_pitcher_rows(facts, links, day, day, None)
    groups = uni_group_rows(facts, links, day, day, None)
    for row in dramas:
        session.add(_uni_drama(day, row))
    for row in pitcher_dramas:
        session.add(_uni_pitcher_drama(day, row))
    for row in pitchers:
        session.add(_uni_pitcher(day, row))
    for row in groups:
        session.add(_uni_group(day, row))
    return len(dramas) + len(pitcher_dramas) + len(pitchers) + len(groups)


def _sums(row: dict[str, Any], names: tuple[str, ...]) -> dict[str, Decimal]:
    raw = row.get("_sums") or {}
    return {name: Decimal(str(raw.get(name) or 0)) for name in names}


def _when(value: Any) -> datetime | None:
    if value is None or isinstance(value, datetime):
        return value
    return datetime.fromisoformat(str(value))


def _drama(day: date, mode: str, row: dict[str, Any]) -> ReportManhuaDramaDay:
    sums = _sums(row, MANHUA_BASE)
    return ReportManhuaDramaDay(
        stat_date=day,
        charge_mode=mode,
        series_id=int(row["series_id"]),
        panel_key=str(row.get("panel_key") or ""),
        book_name=str(row.get("book_name") or ""),
        drama_type=str(row.get("drama_type") or ""),
        channel=str(row.get("channel") or ""),
        publish_date=row.get("publish_date"),
        pitcher_ids=list(row.get("pitcher_ids") or []),
        pitcher_names=list(row.get("pitcher_names") or []),
        department_names=list(row.get("department_names") or []),
        bid_types=list(row.get("bid_types") or []),
        panel_names=list(row.get("panel_names") or []),
        costed_promotion_ids=list(row.get("costed_promotion_ids") or []),
        **sums,
    )


def _project(day: date, mode: str, row: dict[str, Any]) -> ReportManhuaProjectDay:
    sums = _sums(row, MANHUA_BASE)
    budget = row.get("project_budget")
    goal = row.get("roi_goal")
    return ReportManhuaProjectDay(
        stat_date=day,
        charge_mode=mode,
        project_id=int(row["project_id"]),
        project_name=str(row.get("project_name") or ""),
        series_id=int(row.get("series_id") or 0),
        book_name=str(row.get("book_name") or ""),
        pitcher_id=int(row.get("pitcher_id") or 0),
        pitcher_name=str(row.get("pitcher") or ""),
        department_name=str(row.get("team") or ""),
        bid_type=str(row.get("bid_type") or ""),
        drama_type=str(row.get("drama_type") or ""),
        channel=str(row.get("channel") or ""),
        panel=str(row.get("panel") or ""),
        publish_date=row.get("publish_date"),
        created_at=_when(row.get("created_at")),
        first_cost_time=row.get("first_cost_time"),
        project_budget=None if budget is None else Decimal(str(budget)),
        roi_goal=None if goal is None else Decimal(str(goal)),
        **sums,
    )


def _promotion(day: date, mode: str, row: dict[str, Any]) -> ReportManhuaPromotionDay:
    base = _project(day, mode, row)
    return ReportManhuaPromotionDay(
        stat_date=day,
        charge_mode=mode,
        promotion_id=int(row["promotion_id"]),
        promotion_name=str(row.get("promotion_name") or ""),
        project_id=base.project_id,
        project_name=base.project_name,
        series_id=base.series_id,
        book_name=base.book_name,
        pitcher_id=base.pitcher_id,
        pitcher_name=base.pitcher_name,
        department_name=base.department_name,
        bid_type=base.bid_type,
        drama_type=base.drama_type,
        channel=base.channel,
        panel=base.panel,
        publish_date=base.publish_date,
        created_at=base.created_at,
        first_cost_time=base.first_cost_time,
        project_budget=base.project_budget,
        roi_goal=base.roi_goal,
        stat_cost=base.stat_cost,
        stat_pay_amount=base.stat_pay_amount,
        attribution_game_in_app_ltv_1day=base.attribution_game_in_app_ltv_1day,
        attribution_game_in_app_ltv_8days=base.attribution_game_in_app_ltv_8days,
        attribution_micro_game_0d_ltv=base.attribution_micro_game_0d_ltv,
        attribution_micro_game_7d_ltv=base.attribution_micro_game_7d_ltv,
        show_cnt=base.show_cnt,
        click_cnt=base.click_cnt,
        convert_cnt=base.convert_cnt,
        active=base.active,
    )


def _uni_money(row: dict[str, Any]) -> dict[str, Any]:
    sums = _sums(row, (*UNI_MONEY, "new_project_count", "all_show_cnt_trend", "all_click_cnt_trend"))
    sums["new_project_count"] = int(sums["new_project_count"])
    sums["all_show_cnt_trend"] = int(sums["all_show_cnt_trend"])
    sums["all_click_cnt_trend"] = int(sums["all_click_cnt_trend"])
    return sums


def backfill_uni_show_click(connection) -> None:
    """已有日行补展示、点击。只 UPDATE，对不上的行保持 0。"""
    connection.execute(
        text(
            """
            UPDATE report_uni_drama_day AS d
            SET all_show_cnt_trend = agg.show_cnt,
                all_click_cnt_trend = agg.click_cnt
            FROM (
                SELECT substr(r.stat_time_hour, 1, 10) AS stat_day,
                       map.series_id,
                       COALESCE(SUM(r.all_show_cnt_trend), 0) AS show_cnt,
                       COALESCE(SUM(r.all_click_cnt_trend), 0) AS click_cnt
                FROM oe_uni_project_report AS r
                JOIN (
                    SELECT DISTINCT a.ocean_project_id, t.series_id
                    FROM uni_native_task_account AS a
                    JOIN uni_native_task AS t ON t.id = a.task_id AND t.is_deleted = 0
                    WHERE a.is_deleted = 0 AND a.ocean_project_id IS NOT NULL
                ) AS map ON map.ocean_project_id = r.cdp_project_id
                WHERE r.is_deleted = 0
                GROUP BY substr(r.stat_time_hour, 1, 10), map.series_id
            ) AS agg
            WHERE d.stat_date = agg.stat_day::date
              AND d.series_id = agg.series_id
            """
        )
    )
    connection.execute(
        text(
            """
            UPDATE report_uni_pitcher_drama_day AS d
            SET all_show_cnt_trend = agg.show_cnt,
                all_click_cnt_trend = agg.click_cnt
            FROM (
                SELECT substr(r.stat_time_hour, 1, 10) AS stat_day,
                       map.pitcher_user_id,
                       map.series_id,
                       COALESCE(SUM(r.all_show_cnt_trend), 0) AS show_cnt,
                       COALESCE(SUM(r.all_click_cnt_trend), 0) AS click_cnt
                FROM oe_uni_project_report AS r
                JOIN (
                    SELECT DISTINCT a.ocean_project_id, t.series_id, t.pitcher_user_id
                    FROM uni_native_task_account AS a
                    JOIN uni_native_task AS t ON t.id = a.task_id AND t.is_deleted = 0
                    WHERE a.is_deleted = 0 AND a.ocean_project_id IS NOT NULL
                ) AS map ON map.ocean_project_id = r.cdp_project_id
                WHERE r.is_deleted = 0
                GROUP BY substr(r.stat_time_hour, 1, 10), map.pitcher_user_id, map.series_id
            ) AS agg
            WHERE d.stat_date = agg.stat_day::date
              AND d.pitcher_id = agg.pitcher_user_id
              AND d.series_id = agg.series_id
            """
        )
    )
    connection.execute(
        text(
            """
            UPDATE report_uni_pitcher_day AS d
            SET all_show_cnt_trend = agg.show_cnt,
                all_click_cnt_trend = agg.click_cnt
            FROM (
                SELECT substr(r.stat_time_hour, 1, 10) AS stat_day,
                       map.pitcher_user_id,
                       COALESCE(SUM(r.all_show_cnt_trend), 0) AS show_cnt,
                       COALESCE(SUM(r.all_click_cnt_trend), 0) AS click_cnt
                FROM oe_uni_project_report AS r
                JOIN (
                    SELECT DISTINCT a.ocean_project_id, t.pitcher_user_id
                    FROM uni_native_task_account AS a
                    JOIN uni_native_task AS t ON t.id = a.task_id AND t.is_deleted = 0
                    WHERE a.is_deleted = 0 AND a.ocean_project_id IS NOT NULL
                ) AS map ON map.ocean_project_id = r.cdp_project_id
                WHERE r.is_deleted = 0
                GROUP BY substr(r.stat_time_hour, 1, 10), map.pitcher_user_id
            ) AS agg
            WHERE d.stat_date = agg.stat_day::date
              AND d.pitcher_id = agg.pitcher_user_id
            """
        )
    )
    connection.execute(
        text(
            """
            UPDATE report_uni_group_day AS d
            SET all_show_cnt_trend = agg.show_cnt,
                all_click_cnt_trend = agg.click_cnt
            FROM (
                SELECT substr(r.stat_time_hour, 1, 10) AS stat_day,
                       map.department_id,
                       COALESCE(SUM(r.all_show_cnt_trend), 0) AS show_cnt,
                       COALESCE(SUM(r.all_click_cnt_trend), 0) AS click_cnt
                FROM oe_uni_project_report AS r
                JOIN (
                    SELECT DISTINCT a.ocean_project_id, u.department_id
                    FROM uni_native_task_account AS a
                    JOIN uni_native_task AS t ON t.id = a.task_id AND t.is_deleted = 0
                    JOIN users AS u ON u.id = t.pitcher_user_id
                    WHERE a.is_deleted = 0
                      AND a.ocean_project_id IS NOT NULL
                      AND u.department_id IS NOT NULL
                ) AS map ON map.ocean_project_id = r.cdp_project_id
                WHERE r.is_deleted = 0
                GROUP BY substr(r.stat_time_hour, 1, 10), map.department_id
            ) AS agg
            WHERE d.stat_date = agg.stat_day::date
              AND d.department_id = agg.department_id
            """
        )
    )


def _uni_drama(day: date, row: dict[str, Any]) -> ReportUniDramaDay:
    return ReportUniDramaDay(
        stat_date=day,
        series_id=int(row["series_id"]),
        book_name=str(row.get("book_name") or ""),
        platform_name=str(row.get("platform_name") or ""),
        pitcher_ids=list(row.get("pitcher_ids") or []),
        **_uni_money(row),
    )


def _uni_pitcher_drama(day: date, row: dict[str, Any]) -> ReportUniPitcherDramaDay:
    return ReportUniPitcherDramaDay(
        stat_date=day,
        pitcher_id=int(row["pitcher_user_id"]),
        pitcher_name=str(row.get("pitcher_name") or ""),
        series_id=int(row["series_id"]),
        book_name=str(row.get("book_name") or ""),
        platform_name=str(row.get("platform_name") or ""),
        **_uni_money(row),
    )


def _uni_pitcher(day: date, row: dict[str, Any]) -> ReportUniPitcherDay:
    return ReportUniPitcherDay(
        stat_date=day,
        pitcher_id=int(row["pitcher_user_id"]),
        pitcher_name=str(row.get("pitcher_name") or ""),
        **_uni_money(row),
    )


def _uni_group(day: date, row: dict[str, Any]) -> ReportUniGroupDay:
    return ReportUniGroupDay(
        stat_date=day,
        department_id=int(row["department_id"]),
        department_name=str(row.get("department_name") or ""),
        **_uni_money(row),
    )
