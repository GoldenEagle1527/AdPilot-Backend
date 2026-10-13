"""巨量广告列表。账户菜单 32，项目 33，广告 34，素材 35，全域项目 37。"""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.core.envelope import Envelope, success
from app.core.pagination import PageData
from app.modules.ocean_ads.columns import assert_menu, read_columns, save_columns
from app.modules.ocean_ads.pages import (
    batch_projects,
    batch_promotions,
    list_materials,
    list_projects,
    list_promotion_names,
    list_promotions,
    list_uni_projects,
    update_project_budgets,
)
from app.modules.ocean_ads.schema import (
    AccountItem,
    AccountQuery,
    ColumnData,
    ColumnQuery,
    ColumnWrite,
    MaterialItem,
    MaterialQuery,
    ProjectBatchResult,
    ProjectBatchWrite,
    ProjectBudgetResult,
    ProjectBudgetWrite,
    ProjectItem,
    ProjectQuery,
    PromotionBatchResult,
    PromotionBatchWrite,
    PromotionItem,
    PromotionNameItem,
    PromotionNameQuery,
    PromotionQuery,
    UniProjectItem,
    UniProjectQuery,
)
from app.modules.ocean_ads.service import list_accounts
from app.modules.system_admin import require_menu

router = APIRouter(prefix="/api/v1/ocean-ads", tags=["ocean-ads"])

SessionDep = Annotated[AsyncSession, Depends(get_session)]
PrincipalDep = Annotated[dict[str, Any], Depends(require_menu("32"))]
ColumnPrincipal = Annotated[dict[str, Any], Depends(require_menu("32", "33", "34", "35"))]


@router.get("/accounts", response_model=Envelope[PageData[AccountItem]], summary="分页查询巨量广告账户")
async def get_accounts(
    session: SessionDep,
    principal: PrincipalDep,
    query: Annotated[AccountQuery, Query()],
) -> dict[str, Any]:
    """标准、全域分两个页签。效果数读本地素材表，余额再向巨量查。"""
    return success(await list_accounts(session, query, principal))


@router.get("/columns", response_model=Envelope[ColumnData], summary="读取自定义列")
async def get_columns(
    session: SessionDep,
    principal: ColumnPrincipal,
    query: Annotated[ColumnQuery, Query()],
) -> dict[str, Any]:
    """当前登录人在这个菜单上保存的列和顺序。没存过则是默认列。"""
    await assert_menu(session, principal, query.menu_id)
    return success(await read_columns(session, int(principal["id"]), query.menu_id))


@router.put("/columns", response_model=Envelope[ColumnData], summary="保存自定义列")
async def put_columns(
    session: SessionDep,
    principal: ColumnPrincipal,
    body: ColumnWrite,
) -> dict[str, Any]:
    """替换当前登录人在这个菜单上的勾选和顺序。"""
    await assert_menu(session, principal, body.menu_id)
    data = await save_columns(session, int(principal["id"]), body.menu_id, body.columns)
    await session.commit()
    return success(data)


@router.get("/projects", response_model=Envelope[PageData[ProjectItem]], summary="分页查询项目")
async def get_projects(
    session: SessionDep,
    principal: Annotated[dict[str, Any], Depends(require_menu("33"))],
    query: Annotated[ProjectQuery, Query()],
) -> dict[str, Any]:
    """列出项目。状态传开启或暂停。标准和全域都包含。"""
    return success(await list_projects(session, query, principal))


@router.post("/projects/batch", response_model=Envelope[ProjectBatchResult], summary="批量开启、暂停或删除项目")
async def post_project_batch(
    session: SessionDep,
    principal: Annotated[dict[str, Any], Depends(require_menu("33"))],
    body: ProjectBatchWrite,
) -> dict[str, Any]:
    """项目改状态后，该项目下未删除的广告一起改。开启、暂停、删除都通知巨量。巨量接受的删除才在本库软删。"""
    data = await batch_projects(session, body, principal)
    await session.commit()
    return success(data)


@router.post("/projects/budget", response_model=Envelope[ProjectBudgetResult], summary="批量修改项目预算")
async def post_project_budget(
    session: SessionDep,
    principal: Annotated[dict[str, Any], Depends(require_menu("33"))],
    body: ProjectBudgetWrite,
) -> dict[str, Any]:
    """改的是项目目标预算，并通知巨量。看不了的项目不出现在返回里。"""
    data = await update_project_budgets(session, body, principal)
    await session.commit()
    return success(data)


@router.get("/promotions", response_model=Envelope[PageData[PromotionItem]], summary="分页查询广告")
async def get_promotions(
    session: SessionDep,
    principal: Annotated[dict[str, Any], Depends(require_menu("34"))],
    query: Annotated[PromotionQuery, Query()],
) -> dict[str, Any]:
    """父项目暂停时，广告状态为已被项目暂停。"""
    return success(await list_promotions(session, query, principal))


@router.post("/promotions/batch", response_model=Envelope[PromotionBatchResult], summary="批量开启、暂停或删除广告")
async def post_promotion_batch(
    session: SessionDep,
    principal: Annotated[dict[str, Any], Depends(require_menu("34"))],
    body: PromotionBatchWrite,
) -> dict[str, Any]:
    """只改选中的广告，不改所属项目。开启、暂停、删除都通知巨量。巨量接受的删除才在本库软删。"""
    data = await batch_promotions(session, body, principal)
    await session.commit()
    return success(data)


@router.get("/promotion-names", response_model=Envelope[PageData[PromotionNameItem]], summary="广告名称下拉")
async def get_promotion_names(
    session: SessionDep,
    principal: Annotated[dict[str, Any], Depends(require_menu("34"))],
    query: Annotated[PromotionNameQuery, Query()],
) -> dict[str, Any]:
    """当前登录人能看到的未删除广告名。一个名称对应一条广告。"""
    return success(await list_promotion_names(session, query, principal))


@router.get("/materials", response_model=Envelope[PageData[MaterialItem]], summary="分页查询素材")
async def get_materials(
    session: SessionDep,
    principal: Annotated[dict[str, Any], Depends(require_menu("35"))],
    query: Annotated[MaterialQuery, Query()],
) -> dict[str, Any]:
    """按选定的一天加总。投手须带短剧投手标签。所属项目或广告已软删除的不显示。"""
    return success(await list_materials(session, query, principal))


@router.get("/uni-projects", response_model=Envelope[PageData[UniProjectItem]], summary="分页查询全域项目")
async def get_uni_projects(
    session: SessionDep,
    principal: Annotated[dict[str, Any], Depends(require_menu("37"))],
    query: Annotated[UniProjectQuery, Query()],
) -> dict[str, Any]:
    """只列出全域投放的项目。创建时的 ROI 系数在查到巨量新值后更新。"""
    data = await list_uni_projects(session, query, principal)
    await session.commit()
    return success(data)
