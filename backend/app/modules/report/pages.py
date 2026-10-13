"""一页报表：列表读日表，趋势和时速读小时快照。不调巨量。"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.envelope import ApiError
from app.core.pagination import PageParams, page_slice
from app.modules.report import crud, read_serving
from app.modules.report.schema import MEDIA_OCEAN, ManhuaQuery, ManhuaTrendQuery, UniQuery, UniSpeedQuery
from app.modules.report.service import manhua_summary, manhua_trend, sort_rows, uni_speed, uni_summary
from app.modules.system_admin.domain.scope import DataScope

_NOT_FOUND = "报表行不存在或不可见"


async def manhua_rows(
    session: AsyncSession, query: ManhuaQuery, level: str, user_id: int | None
) -> list[dict[str, Any]]:
    """筛选、权限后排好序的全部行。媒体不是巨量时为空。"""
    if query.media != MEDIA_OCEAN:
        return []
    if level == "drama":
        rows = await read_serving.manhua_drama_rows(session, query, user_id)
    elif level == "project":
        rows = await read_serving.manhua_project_rows(session, query, user_id)
    else:
        rows = await read_serving.manhua_promotion_rows(session, query, user_id)
    return sort_rows(rows, query.sort_by, query.sort_order)


async def manhua_page(
    session: AsyncSession, query: ManhuaQuery, level: str, user_id: int | None
) -> dict[str, Any]:
    rows = await manhua_rows(session, query, level, user_id)
    data = page_slice(rows, PageParams(page=query.page, page_size=query.page_size))
    data["summary"] = manhua_summary(rows)
    return data


async def manhua_trend_data(
    session: AsyncSession, query: ManhuaTrendQuery, user_id: int | None, now: datetime
) -> dict[str, Any]:
    """趋势弹框。剧目按该剧（付费再加面板）全部投手合计；项目、计划须是自己的。负责人不限投手。"""
    if query.grain == "drama":
        links = await crud.standard_links(session, charge_mode=query.charge_mode, series_id=query.id)
        if query.panel is not None:
            links = {key: link for key, link in links.items() if link.bid_panel == query.panel}
        if not links or (user_id is not None and not any(link.pitcher_id == user_id for link in links.values())):
            raise ApiError(404, _NOT_FOUND)
        hourly = await crud.manhua_hourly(session, query.date, project_ids=links.keys())
    elif query.grain == "project":
        links = await crud.standard_links(session, charge_mode=query.charge_mode, project_ids=[query.id])
        link = links.get(query.id)
        if link is None or (user_id is not None and link.pitcher_id != user_id):
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
        if link is None or (user_id is not None and link.pitcher_id != user_id):
            raise ApiError(404, _NOT_FOUND)
        hourly = await crud.manhua_hourly(session, query.date, promotion_id=query.id)
    return manhua_trend(query.date, hourly, now)


async def visible_departments(session: AsyncSession, scope: DataScope, *, see_all: bool = False) -> set[int] | None:
    """组报表可见部门。see_all 时返回 None，表示不限制部门。范围为空只看自己所在部门。"""
    if see_all:
        return None
    if not scope.self_only and scope.department_ids:
        return {int(item) for item in scope.department_ids}
    own = await crud.user_department_id(session, scope.user_id)
    return set() if own is None else {int(own)}


async def uni_page(
    session: AsyncSession,
    query: UniQuery,
    kind: str,
    scope: DataScope,
    *,
    see_all: bool = False,
) -> dict[str, Any]:
    """全域四个列表。kind：dramas、pitcher-dramas、pitchers、groups。负责人看全部。"""
    user_id = None if see_all else scope.user_id
    if kind == "dramas":
        rows = await read_serving.uni_drama_rows(session, query, user_id)
    elif kind == "pitcher-dramas":
        rows = await read_serving.uni_pitcher_drama_rows(session, query, user_id)
    elif kind == "pitchers":
        rows = await read_serving.uni_pitcher_rows(session, query, user_id)
    else:
        rows = await read_serving.uni_group_rows(
            session, query, await visible_departments(session, scope, see_all=see_all)
        )
    rows = sort_rows(rows, query.sort_by, query.sort_order)
    data = page_slice(rows, PageParams(page=query.page, page_size=query.page_size))
    data["summary"] = uni_summary(rows)
    return data


async def uni_speed_data(
    session: AsyncSession,
    query: UniSpeedQuery,
    scope: DataScope,
    now: datetime,
    *,
    see_all: bool = False,
) -> dict[str, Any]:
    """时速弹框。剧目按该剧全部投手合计，投手只能看自己，组只能看可见部门。负责人不限。"""
    user_id = None if see_all else scope.user_id
    if query.scope == "drama":
        links = await crud.uni_links(session, series_id=query.id)
        if not links or (user_id is not None and not any(link.pitcher_id == user_id for link in links.values())):
            raise ApiError(404, _NOT_FOUND)
    elif query.scope == "pitcher":
        if user_id is not None and query.id != user_id:
            raise ApiError(404, _NOT_FOUND)
        links = await crud.uni_links(session, pitcher_id=query.id)
        if see_all and not links:
            raise ApiError(404, _NOT_FOUND)
    else:
        visible = await visible_departments(session, scope, see_all=see_all)
        if visible is not None and query.id not in visible:
            raise ApiError(404, _NOT_FOUND)
        links = await crud.uni_links(session, department_id=query.id)
    current = await crud.uni_hourly_cost(session, query.date, links.keys())
    previous = await crud.uni_hourly_cost(session, query.date - timedelta(days=1), links.keys())
    return uni_speed(query.date, current, previous, now)
