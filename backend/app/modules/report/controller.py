"""数据报表 HTTP。只读快照，不调巨量。漫剧付费菜单 9、免费菜单 5；全域短剧 13、投手 14、组 15。"""

from __future__ import annotations

from typing import Annotated, Any
from urllib.parse import quote

from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import require_token
from app.core.db import get_session
from app.core.envelope import ApiError, Envelope, success
from app.core.times import beijing_now
from app.modules.report.export import workbook_bytes
from app.modules.report.home import HomeQuery as HomeCall
from app.modules.report.home import home_view, save_home_fields
from app.modules.report.pages import (
    manhua_page,
    manhua_rows,
    manhua_trend_data,
    uni_page,
    uni_speed_data,
)
from app.modules.report.schema import (
    HomeData,
    HomeFieldsBody,
    HomeFieldsData,
    HomePageQuery,
    ManhuaDramaItem,
    ManhuaDramaQuery,
    ManhuaExportQuery,
    ManhuaMetrics,
    ManhuaProjectItem,
    ManhuaProjectQuery,
    ManhuaPromotionItem,
    ManhuaTrendData,
    ManhuaTrendQuery,
    ReportPage,
    UniDramaItem,
    UniGroupItem,
    UniMetrics,
    UniPitcherDramaItem,
    UniPitcherItem,
    UniQuery,
    UniSpeedData,
    UniSpeedQuery,
)
from app.modules.system_admin import require_menu
from app.modules.system_admin.domain.access import effective_menu_ids, user_by_login
from app.modules.system_admin.domain.enums import ROLE_KIND_OWNER
from app.modules.system_admin.domain.models import User
from app.modules.system_admin.domain.scope import resolve_data_scope

router = APIRouter(prefix="/api/v1/reports", tags=["reports"])

SessionDep = Annotated[AsyncSession, Depends(get_session)]
ManhuaMenu = Annotated[dict[str, Any], Depends(require_menu("9", "5"))]
UniDramaMenu = Annotated[dict[str, Any], Depends(require_menu("13"))]
UniPitcherMenu = Annotated[dict[str, Any], Depends(require_menu("14"))]
UniGroupMenu = Annotated[dict[str, Any], Depends(require_menu("15"))]
UniAnyMenu = Annotated[dict[str, Any], Depends(require_menu("13", "14", "15"))]

_CHARGE_MENU = {"IAP": "9", "IAA": "5"}
_SPEED_MENU = {"drama": "13", "pitcher": "14", "group": "15"}
_FORBIDDEN = "已登录但无对应菜单或组件"
_XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


async def _assert_menu(session: AsyncSession, principal: dict[str, Any], menu_id: str) -> None:
    """依赖只放行了任一报表菜单，这里按收费模式或时速范围再卡具体节点。"""
    granted = principal.get("menu_ids")
    if not isinstance(granted, list):
        user = await user_by_login(session, str(principal["login_account"]))
        if user is None or not user.enabled:
            raise ApiError(403, _FORBIDDEN)
        granted = list(await effective_menu_ids(session, user))
    if menu_id not in {str(item) for item in granted}:
        raise ApiError(403, _FORBIDDEN)


def _user_id(principal: dict[str, Any]) -> int:
    return int(principal["id"])


async def _viewer_id(session: AsyncSession, principal: dict[str, Any]) -> int | None:
    """负责人看全部报表，返回空。其余账号只看自己是投手的行。"""
    if principal.get("role_kind") == ROLE_KIND_OWNER:
        return None
    getter = getattr(session, "get", None)
    if not callable(getter):
        return _user_id(principal)
    user = await getter(User, _user_id(principal))
    if user is not None and user.role_kind == ROLE_KIND_OWNER:
        return None
    return _user_id(principal)


@router.get(
    "/manhua/dramas",
    response_model=Envelope[ReportPage[ManhuaDramaItem, ManhuaMetrics]],
    summary="漫剧剧目报表（R1IAP / R1IAA）",
)
async def get_manhua_dramas(
    session: SessionDep,
    principal: ManhuaMenu,
    query: Annotated[ManhuaDramaQuery, Query()],
) -> dict[str, Any]:
    """所选区间一部剧一行，付费再按面板拆行。当前用户须是该行投手之一。"""
    await _assert_menu(session, principal, _CHARGE_MENU[query.charge_mode])
    return success(await manhua_page(session, query, "drama", await _viewer_id(session, principal)))


@router.get(
    "/manhua/projects",
    response_model=Envelope[ReportPage[ManhuaProjectItem, ManhuaMetrics]],
    summary="漫剧项目报表（IAP项目 / IAA项目）",
)
async def get_manhua_projects(
    session: SessionDep,
    principal: ManhuaMenu,
    query: Annotated[ManhuaProjectQuery, Query()],
) -> dict[str, Any]:
    """所选区间一个项目一行。只看自己是投手的项目。"""
    await _assert_menu(session, principal, _CHARGE_MENU[query.charge_mode])
    return success(await manhua_page(session, query, "project", await _viewer_id(session, principal)))


@router.get(
    "/manhua/promotions",
    response_model=Envelope[ReportPage[ManhuaPromotionItem, ManhuaMetrics]],
    summary="漫剧计划报表（IAP计划 / IAA计划）",
)
async def get_manhua_promotions(
    session: SessionDep,
    principal: ManhuaMenu,
    query: Annotated[ManhuaProjectQuery, Query()],
) -> dict[str, Any]:
    """所选区间一条广告一行。只看自己是投手的广告。"""
    await _assert_menu(session, principal, _CHARGE_MENU[query.charge_mode])
    return success(await manhua_page(session, query, "promotion", await _viewer_id(session, principal)))


@router.get(
    "/manhua/trend",
    response_model=Envelope[ManhuaTrendData],
    summary="漫剧趋势弹框",
)
async def get_manhua_trend(
    session: SessionDep,
    principal: ManhuaMenu,
    query: Annotated[ManhuaTrendQuery, Query()],
) -> dict[str, Any]:
    """所选一天按小时的消耗和付费金额。还没到的小时不返回。"""
    await _assert_menu(session, principal, _CHARGE_MENU[query.charge_mode])
    return success(await manhua_trend_data(session, query, await _viewer_id(session, principal), beijing_now()))


@router.get(
    "/manhua/export",
    summary="漫剧报表导出 Excel",
    response_class=Response,
    responses={200: {"content": {_XLSX: {}}, "description": "xlsx 文件"}},
)
async def get_manhua_export(
    session: SessionDep,
    principal: ManhuaMenu,
    query: Annotated[ManhuaExportQuery, Query()],
) -> Response:
    """与对应列表同筛选、同排序的全部行，不分页。"""
    await _assert_menu(session, principal, _CHARGE_MENU[query.charge_mode])
    rows = await manhua_rows(session, query, query.level, await _viewer_id(session, principal))
    content = workbook_bytes(query.level, rows)
    name = f"漫剧报表-{query.charge_mode}-{query.level}-{query.date_start}_{query.date_end}.xlsx"
    return Response(
        content=content,
        media_type=_XLSX,
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{quote(name)}"},
    )


@router.get(
    "/uni/dramas",
    response_model=Envelope[ReportPage[UniDramaItem, UniMetrics]],
    summary="全域短剧收益",
)
async def get_uni_dramas(
    session: SessionDep,
    principal: UniDramaMenu,
    query: Annotated[UniQuery, Query()],
) -> dict[str, Any]:
    """所选区间一部剧一行。当前用户须是该剧投手之一。"""
    scope = await resolve_data_scope(session, principal)
    return success(await uni_page(session, query, "dramas", scope, see_all=await _viewer_id(session, principal) is None))


@router.get(
    "/uni/pitcher-dramas",
    response_model=Envelope[ReportPage[UniPitcherDramaItem, UniMetrics]],
    summary="全域投手短剧收益",
)
async def get_uni_pitcher_dramas(
    session: SessionDep,
    principal: UniDramaMenu,
    query: Annotated[UniQuery, Query()],
) -> dict[str, Any]:
    """同短剧收益，多一格投手（多人用、连接）。"""
    scope = await resolve_data_scope(session, principal)
    return success(
        await uni_page(session, query, "pitcher-dramas", scope, see_all=await _viewer_id(session, principal) is None)
    )


@router.get(
    "/uni/pitchers",
    response_model=Envelope[ReportPage[UniPitcherItem, UniMetrics]],
    summary="全域投手报表",
)
async def get_uni_pitchers(
    session: SessionDep,
    principal: UniPitcherMenu,
    query: Annotated[UniQuery, Query()],
) -> dict[str, Any]:
    """一个投手一天一行。只看自己。"""
    scope = await resolve_data_scope(session, principal)
    return success(await uni_page(session, query, "pitchers", scope, see_all=await _viewer_id(session, principal) is None))


@router.get(
    "/uni/groups",
    response_model=Envelope[ReportPage[UniGroupItem, UniMetrics]],
    summary="全域组报表",
)
async def get_uni_groups(
    session: SessionDep,
    principal: UniGroupMenu,
    query: Annotated[UniQuery, Query()],
) -> dict[str, Any]:
    """一个部门一天一行。可见部门是数据范围；范围为空只看本部门。"""
    scope = await resolve_data_scope(session, principal)
    return success(await uni_page(session, query, "groups", scope, see_all=await _viewer_id(session, principal) is None))


@router.get(
    "/uni/speed",
    response_model=Envelope[UniSpeedData],
    summary="全域时速弹框",
)
async def get_uni_speed(
    session: SessionDep,
    principal: UniAnyMenu,
    query: Annotated[UniSpeedQuery, Query()],
) -> dict[str, Any]:
    """所选日与前一天按小时的全域消耗，带分时增长率。回收数组为空。"""
    await _assert_menu(session, principal, _SPEED_MENU[query.scope])
    scope = await resolve_data_scope(session, principal)
    return success(
        await uni_speed_data(
            session, query, scope, beijing_now(), see_all=await _viewer_id(session, principal) is None
        )
    )


TokenUser = Annotated[dict[str, Any], Depends(require_token)]


@router.get("/home", response_model=Envelope[HomeData], response_model_exclude_none=True, summary="首页")
async def get_home(
    session: SessionDep,
    principal: TokenUser,
    query: Annotated[HomePageQuery, Query()],
) -> dict[str, Any]:
    """五张卡和一条曲线。只读快照，不查菜单。"""
    return success(
        await home_view(
            session,
            principal,
            HomeCall(
                surface=query.surface,
                charge_mode=query.charge_mode,
                date_start=query.date_start,
                date_end=query.date_end,
                user_ids=tuple(query.user_ids),
                department_ids=tuple(query.department_ids),
                curve=query.curve,
            ),
        )
    )


@router.put("/home/fields", response_model=Envelope[HomeFieldsData], summary="首页自选字段")
async def put_home_fields(
    session: SessionDep,
    principal: TokenUser,
    body: HomeFieldsBody,
) -> dict[str, Any]:
    """整行替换当前账号该表面的三个自选。不查菜单。"""
    return success(await save_home_fields(session, _user_id(principal), body.surface, list(body.fields)))
