"""利润报表和素材报表的 HTTP。读日表，不调巨量。"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Annotated, Any

from fastapi import Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.envelope import Envelope, success
from app.core.pagination import PageParams, page_slice
from app.modules.report import ledger_store
from app.modules.report.controller import SessionDep, _assert_menu, _user_id, _viewer_id, router
from app.modules.report.ledger import (
    drama_editor_table,
    drama_spend_table,
    editor_only,
    editor_spend_table,
    editor_stat_table,
    group_avg_roi,
    locked_pitcher,
    material_detail_table,
    material_spend_table,
    narrow_departments,
    nb_table,
    paged,
    profit_table,
    profit_visible,
    video_spend_table,
)
from app.modules.report.ledger_schema import (
    DeletedRoi,
    DramaEditorPage,
    DramaEditorQuery,
    DramaSpendPage,
    DramaSpendQuery,
    EditorSpendPage,
    EditorSpendQuery,
    EditorStatPage,
    EditorStatQuery,
    MaterialDetailPage,
    MaterialDetailQuery,
    MaterialSpendPage,
    MaterialSpendQuery,
    NbDramaPage,
    NbDramaQuery,
    ProfitDailyQuery,
    ProfitDatePage,
    ProfitDepartmentPage,
    ProfitGroupPitcherQuery,
    ProfitGroupQuery,
    ProfitOverviewQuery,
    ProfitPitcherPage,
    ProfitPitcherQuery,
    ProfitPlatformPage,
    RoiItem,
    RoiPage,
    RoiQuery,
    RoiWrite,
    VideoSpendPage,
    VideoSpendQuery,
)
from app.modules.report.pages import visible_departments
from app.modules.system_admin import require_menu
from app.modules.system_admin.domain.scope import resolve_data_scope

OverviewMenu = Annotated[dict[str, Any], Depends(require_menu("23"))]
DailyMenu = Annotated[dict[str, Any], Depends(require_menu("24"))]
PitcherMenu = Annotated[dict[str, Any], Depends(require_menu("28"))]
GroupMenu = Annotated[dict[str, Any], Depends(require_menu("29"))]
SpendMenu = Annotated[dict[str, Any], Depends(require_menu("17"))]
EditorSpendMenu = Annotated[dict[str, Any], Depends(require_menu("18"))]
MaterialMenu = Annotated[dict[str, Any], Depends(require_menu("19"))]
EditorStatMenu = Annotated[dict[str, Any], Depends(require_menu("21"))]


@dataclass(frozen=True)
class Viewer:
    user_id: int
    owner: bool
    admin: bool
    editor_only: bool
    department_id: int | None


async def _viewer(session: AsyncSession, principal: dict[str, Any]) -> Viewer:
    owner = await _viewer_id(session, principal) is None
    user_id = _user_id(principal)
    flags = await ledger_store.account_flags(session, user_id)
    admin = "运营管理员" in flags.role_names
    return Viewer(
        user_id=user_id,
        owner=owner,
        admin=admin,
        editor_only=editor_only(owner=owner, admin=admin, role_names=flags.role_names, tag_names=flags.tag_names),
        department_id=flags.department_id,
    )


async def _departments(session: AsyncSession, principal: dict[str, Any], viewer: Viewer) -> set[int] | None:
    if viewer.owner:
        return None
    scope = await resolve_data_scope(session, principal)
    return await visible_departments(session, scope, see_all=False)


async def _profit(
    session: AsyncSession,
    query: Any,
    group: str,
    *,
    department_ids: set[int] | None,
    pitcher_id: int | None,
) -> dict[str, Any]:
    slices = await ledger_store.profit_slices(session, query.date_start, query.date_end)
    spans = await ledger_store.roi_spans(session)
    visible = [
        row
        for row in slices
        if profit_visible(
            row,
            mode=query.mode,
            drama_type=query.drama_type,
            platform=query.platform,
            department_ids=department_ids,
            pitcher_id=pitcher_id,
        )
    ]
    rows, summary = profit_table(visible, spans, group)
    return paged(rows, summary, query.page, query.page_size, query.sort_by, query.sort_order)


def _editor_id(viewer: Viewer, requested: int | None) -> int | None:
    if viewer.editor_only:
        return viewer.user_id
    return requested


@router.get(
    "/profit/overview",
    response_model=Envelope[ProfitDatePage],
    summary="利润统计概览",
)
async def get_profit_overview(
    session: SessionDep,
    principal: OverviewMenu,
    query: Annotated[ProfitOverviewQuery, Query()],
) -> dict[str, Any]:
    """一天一行。五个统计页签用 mode。负责人看全部部门，其余按数据权限。"""
    viewer = await _viewer(session, principal)
    departments = narrow_departments(await _departments(session, principal, viewer), query.department_id)
    return success(await _profit(session, query, "date", department_ids=departments, pitcher_id=None))


@router.get(
    "/profit/overview/departments",
    response_model=Envelope[ProfitDepartmentPage],
    summary="利润概览按部门展开",
)
async def get_profit_overview_departments(
    session: SessionDep,
    principal: OverviewMenu,
    query: Annotated[ProfitOverviewQuery, Query()],
) -> dict[str, Any]:
    """点某一天时，把 date_start 和 date_end 都传这一天。"""
    viewer = await _viewer(session, principal)
    departments = narrow_departments(await _departments(session, principal, viewer), query.department_id)
    return success(await _profit(session, query, "department", department_ids=departments, pitcher_id=None))


@router.get("/profit/daily", response_model=Envelope[ProfitDatePage], summary="每日利润统计")
async def get_profit_daily(
    session: SessionDep,
    principal: DailyMenu,
    query: Annotated[ProfitDailyQuery, Query()],
) -> dict[str, Any]:
    """一天一行。投手账号只看自己。"""
    viewer = await _viewer(session, principal)
    pitcher = locked_pitcher(
        owner=viewer.owner, admin=viewer.admin, user_id=viewer.user_id, requested=query.pitcher_user_id
    )
    return success(await _profit(session, query, "date", department_ids=None, pitcher_id=pitcher))


@router.get(
    "/profit/daily/platforms",
    response_model=Envelope[ProfitPlatformPage],
    summary="每日利润按平台展开",
)
async def get_profit_daily_platforms(
    session: SessionDep,
    principal: DailyMenu,
    query: Annotated[ProfitDailyQuery, Query()],
) -> dict[str, Any]:
    """点某一天时，起止日期都传这一天。目前只有番茄有数。"""
    viewer = await _viewer(session, principal)
    pitcher = locked_pitcher(
        owner=viewer.owner, admin=viewer.admin, user_id=viewer.user_id, requested=query.pitcher_user_id
    )
    return success(await _profit(session, query, "platform", department_ids=None, pitcher_id=pitcher))


@router.get("/profit/pitchers", response_model=Envelope[ProfitPitcherPage], summary="投手利润统计")
async def get_profit_pitchers(
    session: SessionDep,
    principal: PitcherMenu,
    query: Annotated[ProfitPitcherQuery, Query()],
) -> dict[str, Any]:
    """区间内一个投手一行。部门范围同组报表，负责人看全部。"""
    viewer = await _viewer(session, principal)
    departments = await _departments(session, principal, viewer)
    return success(await _profit(session, query, "pitcher", department_ids=departments, pitcher_id=None))


@router.get("/profit/groups", response_model=Envelope[ProfitDepartmentPage], summary="组利润统计")
async def get_profit_groups(
    session: SessionDep,
    principal: GroupMenu,
    query: Annotated[ProfitGroupQuery, Query()],
) -> dict[str, Any]:
    """区间内一个部门一行。"""
    viewer = await _viewer(session, principal)
    departments = await _departments(session, principal, viewer)
    return success(await _profit(session, query, "department", department_ids=departments, pitcher_id=None))


@router.get(
    "/profit/groups/pitchers",
    response_model=Envelope[ProfitPitcherPage],
    summary="组利润按投手展开",
)
async def get_profit_group_pitchers(
    session: SessionDep,
    principal: GroupMenu,
    query: Annotated[ProfitGroupPitcherQuery, Query()],
) -> dict[str, Any]:
    """点部门后看该部门每个投手。"""
    viewer = await _viewer(session, principal)
    departments = narrow_departments(await _departments(session, principal, viewer), query.department_id)
    return success(await _profit(session, query, "pitcher", department_ids=departments, pitcher_id=None))


@router.get("/profit/roi", response_model=Envelope[RoiPage], summary="ROI 配置列表")
async def get_profit_roi(
    session: SessionDep,
    principal: OverviewMenu,
    query: Annotated[RoiQuery, Query()],
) -> dict[str, Any]:
    """四张利润报表共用。重叠日期取创建时间最新的一条。"""
    del principal
    rows = await ledger_store.list_roi(session)
    return success(page_slice(rows, PageParams(page=query.page, page_size=query.page_size)))


@router.post("/profit/roi", response_model=Envelope[RoiItem], summary="新增 ROI 配置")
async def post_profit_roi(session: SessionDep, principal: OverviewMenu, body: RoiWrite) -> dict[str, Any]:
    """没被任何配置覆盖的统计日，利润按系数 1.00 算。"""
    del principal
    return success(await ledger_store.create_roi(session, body.date_start, body.date_end, body.roi_rate))


@router.put("/profit/roi/{config_id}", response_model=Envelope[RoiItem], summary="修改 ROI 配置")
async def put_profit_roi(
    config_id: int,
    session: SessionDep,
    principal: OverviewMenu,
    body: RoiWrite,
) -> dict[str, Any]:
    del principal
    return success(await ledger_store.update_roi(session, config_id, body.date_start, body.date_end, body.roi_rate))


@router.delete("/profit/roi/{config_id}", response_model=Envelope[DeletedRoi], summary="删除 ROI 配置")
async def delete_profit_roi(config_id: int, session: SessionDep, principal: OverviewMenu) -> dict[str, Any]:
    del principal
    return success(await ledger_store.delete_roi(session, config_id))


@router.get("/materials/spend", response_model=Envelope[MaterialSpendPage], summary="素材消耗")
async def get_material_spend(
    session: SessionDep,
    principal: SpendMenu,
    query: Annotated[MaterialSpendQuery, Query()],
) -> dict[str, Any]:
    """一天一条素材一行。对不上素材库的仍列出，类型和上传者为空。"""
    del principal
    slices = await ledger_store.material_slices(session, query.date_start, query.date_end)
    rows, summary = material_spend_table(slices, pitcher_id=query.pitcher_user_id, uploader_id=query.uploader_id)
    return success(paged(rows, summary, query.page, query.page_size, query.sort_by, query.sort_order))


@router.get(
    "/materials/spend/detail",
    response_model=Envelope[MaterialDetailPage],
    summary="素材消耗数据详情",
)
async def get_material_spend_detail(
    session: SessionDep,
    principal: SpendMenu,
    query: Annotated[MaterialDetailQuery, Query()],
) -> dict[str, Any]:
    """一条广告、一个头条素材一行。千次展示费用是消耗 / 展示 × 1000。"""
    del principal
    slices = await ledger_store.material_slices(session, query.date_start, query.date_end)
    rows, summary = material_detail_table(
        slices,
        video_id=query.video_id,
        ocean_material_id=query.ocean_material_id,
        delivery=query.delivery,
    )
    return success(paged(rows, summary, query.page, query.page_size, query.sort_by, query.sort_order))


@router.get("/materials/editors", response_model=Envelope[EditorSpendPage], summary="剪辑师消耗")
async def get_editor_spend(
    session: SessionDep,
    principal: EditorSpendMenu,
    query: Annotated[EditorSpendQuery, Query()],
) -> dict[str, Any]:
    """一天一个素材手一行。所在组平均 ROI 用登录人部门、当前查询区间，汇总行留空。"""
    viewer = await _viewer(session, principal)
    slices = await ledger_store.material_slices(session, query.date_start, query.date_end)
    avg = group_avg_roi(slices, viewer.department_id)
    rows, summary = editor_spend_table(
        slices,
        uploader_id=query.uploader_id,
        department_id=query.department_id,
        avg_roi=avg,
    )
    return success(paged(rows, summary, query.page, query.page_size, query.sort_by, query.sort_order))


@router.get("/materials/dramas", response_model=Envelope[DramaSpendPage], summary="素材报表 · 短剧统计")
async def get_material_dramas(
    session: SessionDep,
    principal: MaterialMenu,
    query: Annotated[DramaSpendQuery, Query()],
) -> dict[str, Any]:
    """区间内一部有消耗的剧一行。新剧是预估可投日落在区间内。"""
    del principal
    slices = await ledger_store.material_slices(session, query.date_start, query.date_end)
    counts = await ledger_store.library_counts(session, {row.series_id for row in slices})
    rows, summary = drama_spend_table(
        slices,
        counts,
        start=query.date_start,
        end=query.date_end,
        series_name=query.series_name,
        ages=query.drama_age,
    )
    return success(paged(rows, summary, query.page, query.page_size, query.sort_by, query.sort_order))


@router.get(
    "/materials/drama-editors",
    response_model=Envelope[DramaEditorPage],
    summary="素材报表 · 短剧素材手统计",
)
async def get_material_drama_editors(
    session: SessionDep,
    principal: MaterialMenu,
    query: Annotated[DramaEditorQuery, Query()],
) -> dict[str, Any]:
    """一部剧、一个素材手一行。剪辑师和素材手只看自己。素材数合计按剧去重。"""
    viewer = await _viewer(session, principal)
    slices = await ledger_store.material_slices(session, query.date_start, query.date_end)
    counts = await ledger_store.library_counts(session, {row.series_id for row in slices})
    rows, summary = drama_editor_table(
        slices,
        counts,
        start=query.date_start,
        end=query.date_end,
        series_name=query.series_name,
        uploader_id=_editor_id(viewer, query.uploader_id),
        ages=query.drama_age,
    )
    return success(paged(rows, summary, query.page, query.page_size, query.sort_by, query.sort_order))


@router.get("/materials/videos", response_model=Envelope[VideoSpendPage], summary="素材报表 · 素材统计")
async def get_material_videos(
    session: SessionDep,
    principal: MaterialMenu,
    query: Annotated[VideoSpendQuery, Query()],
) -> dict[str, Any]:
    """一条有消耗的素材一行。悬停预览用 file_url，由前端播。"""
    viewer = await _viewer(session, principal)
    slices = await ledger_store.material_slices(session, query.date_start, query.date_end)
    rows, summary = video_spend_table(
        slices,
        start=query.date_start,
        end=query.date_end,
        series_name=query.series_name,
        uploader_id=_editor_id(viewer, query.uploader_id),
        ages=query.drama_age,
    )
    return success(paged(rows, summary, query.page, query.page_size, query.sort_by, query.sort_order))


@router.get("/materials/nb-dramas", response_model=Envelope[NbDramaPage], summary="素材报表 · 未上NB新剧")
async def get_material_nb_dramas(
    session: SessionDep,
    principal: MaterialMenu,
    query: Annotated[NbDramaQuery, Query()],
) -> dict[str, Any]:
    """日期是预估可投日。素材数只数模板名含 NB 或 CBO 的计划里用到的视频。"""
    await _assert_menu(session, principal, "20")
    series = await ledger_store.series_on_estimate(session, query.date_start, query.date_end)
    counts = await ledger_store.nb_material_counts(session, [row.series_id for row in series])
    rows, summary = nb_table(series, counts, series_name=query.series_name)
    return success(paged(rows, summary, query.page, query.page_size, query.sort_by, query.sort_order))


@router.get("/materials/editor-stats", response_model=Envelope[EditorStatPage], summary="剪辑师统计")
async def get_editor_stats(
    session: SessionDep,
    principal: EditorStatMenu,
    query: Annotated[EditorStatQuery, Query()],
) -> dict[str, Any]:
    """一天一个素材手一行。新剧数还要求预估可投日等于这一天。剪辑师和素材手只看自己。"""
    viewer = await _viewer(session, principal)
    slices = await ledger_store.material_slices(session, query.date_start, query.date_end)
    rows, summary = editor_stat_table(
        slices,
        uploader_id=_editor_id(viewer, query.uploader_id),
        department_id=query.department_id,
    )
    return success(paged(rows, summary, query.page, query.page_size, query.sort_by, query.sort_order))
