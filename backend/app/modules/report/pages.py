"""一页报表：读快照和中台表，交给 service 拼行，再分页加汇总。不调巨量。"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.envelope import ApiError
from app.core.pagination import PageParams, page_slice
from app.modules.report import crud
from app.modules.report.schema import MEDIA_OCEAN, ManhuaQuery, ManhuaTrendQuery, UniQuery, UniSpeedQuery
from app.modules.report.service import (
    manhua_drama_rows,
    manhua_project_rows,
    manhua_promotion_rows,
    manhua_summary,
    manhua_trend,
    sort_rows,
    uni_drama_rows,
    uni_group_rows,
    uni_pitcher_rows,
    uni_speed,
    uni_summary,
)
from app.modules.system_admin.domain.scope import DataScope

_NOT_FOUND = "报表行不存在或不可见"


async def manhua_rows(session: AsyncSession, query: ManhuaQuery, level: str, user_id: int) -> list[dict[str, Any]]:
    """筛选、权限后排好序的全部行。媒体不是巨量时为空。"""
    if query.media != MEDIA_OCEAN:
        return []
    facts = await crud.manhua_facts(session, query.date_start, query.date_end, query.charge_mode)
    links = await crud.standard_links(
        session, charge_mode=query.charge_mode, project_ids={fact.project_id for fact in facts}
    )
    if level == "drama":
        rows = manhua_drama_rows(facts, links, query, user_id)
    elif level == "project":
        own = [project_id for project_id, link in links.items() if link.pitcher_id == user_id]
        first = await crud.manhua_first_cost(session, own, by_promotion=False)
        rows = manhua_project_rows(facts, links, query, user_id, first)
    else:
        promotions = await crud.standard_promotions(session, {fact.promotion_id for fact in facts})
        own = [
            promotion_id
            for promotion_id, promotion in promotions.items()
            if (link := links.get(promotion.project_id)) is not None and link.pitcher_id == user_id
        ]
        first = await crud.manhua_first_cost(session, own, by_promotion=True)
        rows = manhua_promotion_rows(facts, links, promotions, query, user_id, first)
    return sort_rows(rows, query.sort_by, query.sort_order)


async def manhua_page(session: AsyncSession, query: ManhuaQuery, level: str, user_id: int) -> dict[str, Any]:
    rows = await manhua_rows(session, query, level, user_id)
    data = page_slice(rows, PageParams(page=query.page, page_size=query.page_size))
    data["summary"] = manhua_summary(rows)
    return data


async def manhua_trend_data(
    session: AsyncSession, query: ManhuaTrendQuery, user_id: int, now: datetime
) -> dict[str, Any]:
    """趋势弹框。剧目按该剧（付费再加面板）全部投手合计；项目、计划须是自己的。"""
    if query.grain == "drama":
        links = await crud.standard_links(session, charge_mode=query.charge_mode, series_id=query.id)
        if query.panel is not None:
            links = {key: link for key, link in links.items() if link.bid_panel == query.panel}
        if not any(link.pitcher_id == user_id for link in links.values()):
            raise ApiError(404, _NOT_FOUND)
        hourly = await crud.manhua_hourly(session, query.date, project_ids=links.keys())
    elif query.grain == "project":
        links = await crud.standard_links(session, charge_mode=query.charge_mode, project_ids=[query.id])
        link = links.get(query.id)
        if link is None or link.pitcher_id != user_id:
            raise ApiError(404, _NOT_FOUND)
        hourly = await crud.manhua_hourly(session, query.date, project_ids=[query.id])
    else:
        promotion = (await crud.standard_promotions(session, [query.id])).get(query.id)
        if promotion is None:
            raise ApiError(404, _NOT_FOUND)
        links = await crud.standard_links(
            session, charge_mode=query.charge_mode, project_ids=[promotion.project_id]
        )
        link = links.get(promotion.project_id)
        if link is None or link.pitcher_id != user_id:
            raise ApiError(404, _NOT_FOUND)
        hourly = await crud.manhua_hourly(session, query.date, promotion_id=query.id)
    return manhua_trend(query.date, hourly, now)


async def visible_departments(session: AsyncSession, scope: DataScope) -> set[int]:
    """组报表可见部门：数据范围；范围为空只看自己所在部门。"""
    if not scope.self_only and scope.department_ids:
        return {int(item) for item in scope.department_ids}
    own = await crud.user_department_id(session, scope.user_id)
    return set() if own is None else {int(own)}


async def uni_page(
    session: AsyncSession,
    query: UniQuery,
    kind: str,
    scope: DataScope,
) -> dict[str, Any]:
    """全域四个列表。kind：dramas、pitcher-dramas、pitchers、groups。"""
    facts = await crud.uni_facts(session, query.date_start, query.date_end)
    links = await crud.uni_links(
        session,
        project_ids={fact.project_id for fact in facts},
        created_between=(query.date_start, query.date_end),
    )
    start, end, user_id = query.date_start, query.date_end, scope.user_id
    if kind in ("dramas", "pitcher-dramas"):
        rows = uni_drama_rows(
            facts, links, start, end, user_id, query.series_name, by_pitcher=kind == "pitcher-dramas"
        )
    elif kind == "pitchers":
        rows = uni_pitcher_rows(facts, links, start, end, user_id)
    else:
        rows = uni_group_rows(facts, links, start, end, await visible_departments(session, scope))
    rows = sort_rows(rows, query.sort_by, query.sort_order)
    data = page_slice(rows, PageParams(page=query.page, page_size=query.page_size))
    data["summary"] = uni_summary(rows)
    return data


async def uni_speed_data(
    session: AsyncSession, query: UniSpeedQuery, scope: DataScope, now: datetime
) -> dict[str, Any]:
    """时速弹框。剧目按该剧全部投手合计，投手只能看自己，组只能看可见部门。"""
    user_id = scope.user_id
    if query.scope == "drama":
        links = await crud.uni_links(session, series_id=query.id)
        if not any(link.pitcher_id == user_id for link in links.values()):
            raise ApiError(404, _NOT_FOUND)
    elif query.scope == "pitcher":
        if query.id != user_id:
            raise ApiError(404, _NOT_FOUND)
        links = await crud.uni_links(session, pitcher_id=query.id)
    else:
        if query.id not in await visible_departments(session, scope):
            raise ApiError(404, _NOT_FOUND)
        links = await crud.uni_links(session, department_id=query.id)
    current = await crud.uni_hourly_cost(session, query.date, links.keys())
    previous = await crud.uni_hourly_cost(session, query.date - timedelta(days=1), links.keys())
    return uni_speed(query.date, current, previous, now)
