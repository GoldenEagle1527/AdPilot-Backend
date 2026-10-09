"""三方剧场 HTTP。平台、应用、同步任务、推广链各用已有菜单。

推广链没有归属用户或部门（常读同步和人工新增都不记创建人），有菜单的人看到全部。
平台、应用、同步任务同样是目录数据，不按部门收窄。
"""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.core.envelope import Envelope, success
from app.core.pagination import PageData
from app.modules.system_admin import require_menu
from app.modules.theater.schema import (
    AppCreate,
    AppItem,
    AppQuery,
    AppStatusUpdate,
    PlatformItem,
    PlatformQuery,
    PlatformUpdate,
    PromotionLinkCreate,
    PromotionLinkCreateResult,
    PromotionLinkItem,
    PromotionLinkQuery,
    PromotionLinkUpdate,
    PromotionTaskItem,
    PromotionTaskQuery,
)
from app.modules.theater.service import (
    create_app,
    create_promotion_links,
    list_apps,
    list_platforms,
    list_promotion_links,
    list_promotion_tasks,
    set_app_status,
    update_platform,
    update_promotion_link,
)

router = APIRouter(prefix="/api/v1/theater", tags=["theater"])

# 三方剧场：82 平台列表，83 平台管理，84 应用列表，85 端原生推广链，86 番茄推广链接同步。
_PLATFORM_LIST = Depends(require_menu("82"))
_PLATFORM_MANAGE = Depends(require_menu("83"))
_APPS = Depends(require_menu("84"))
_PROMOTION_LINKS = Depends(require_menu("85"))
_PROMOTION_TASKS = Depends(require_menu("86"))

SessionDep = Annotated[AsyncSession, Depends(get_session)]


@router.get(
    "/platforms",
    response_model=Envelope[PageData[PlatformItem]],
    summary="分页查询平台",
    dependencies=[_PLATFORM_LIST],
)
async def get_platforms(
    session: SessionDep,
    query: Annotated[PlatformQuery, Query()],
) -> dict[str, Any]:
    """按平台名称模糊、启用状态筛选平台，按排序升序。"""
    return success(await list_platforms(session, query))


@router.patch(
    "/platforms/{platform_id}",
    response_model=Envelope[PlatformItem],
    summary="改平台启用状态和剧场类型开关",
    dependencies=[_PLATFORM_MANAGE],
)
async def patch_platform(
    platform_id: int,
    body: PlatformUpdate,
    session: SessionDep,
) -> dict[str, Any]:
    """只改启用状态、小程序、端原生三项，不传的不动。平台名称和平台码不可改。"""
    return success(await update_platform(session, platform_id, body))


@router.get(
    "/apps",
    response_model=Envelope[PageData[AppItem]],
    summary="分页查询应用",
    dependencies=[_APPS],
)
async def get_apps(
    session: SessionDep,
    query: Annotated[AppQuery, Query()],
) -> dict[str, Any]:
    """按平台、剧场类型、投放模式、剧场风格、状态筛选应用，按创建时间倒序。"""
    return success(await list_apps(session, query))


@router.post(
    "/apps",
    response_model=Envelope[AppItem],
    summary="新增应用",
    dependencies=[_APPS],
)
async def post_app(body: AppCreate, session: SessionDep) -> dict[str, Any]:
    """新增一条有效应用。平台须启用且支持所选剧场类型，同平台剧场名称不重复。"""
    return success(await create_app(session, body))


@router.patch(
    "/apps/{app_id}/status",
    response_model=Envelope[AppItem],
    summary="改应用状态",
    dependencies=[_APPS],
)
async def patch_app_status(app_id: int, body: AppStatusUpdate, session: SessionDep) -> dict[str, Any]:
    """列表里切换有效/无效，只改状态。"""
    return success(await set_app_status(session, app_id, body))


@router.get(
    "/promotion-tasks",
    response_model=Envelope[PageData[PromotionTaskItem]],
    summary="分页查询推广链同步任务",
    dependencies=[_PROMOTION_TASKS],
)
async def get_promotion_tasks(
    session: SessionDep,
    query: Annotated[PromotionTaskQuery, Query()],
) -> dict[str, Any]:
    """按剧名模糊、状态、执行时间筛选，只返回爬虫处理中、成功、失败，按执行时间倒序。"""
    return success(await list_promotion_tasks(session, query))


@router.get(
    "/promotion-links",
    response_model=Envelope[PageData[PromotionLinkItem]],
    summary="分页查询端原生推广链",
    dependencies=[_PROMOTION_LINKS],
)
async def get_promotion_links(
    session: SessionDep,
    query: Annotated[PromotionLinkQuery, Query()],
) -> dict[str, Any]:
    """按首发日期段、剧场、剧名、启用状态筛选推广链，按创建时间倒序。"""
    return success(await list_promotion_links(session, query))


@router.post(
    "/promotion-links",
    response_model=Envelope[PromotionLinkCreateResult],
    summary="人工新增端原生推广链",
    dependencies=[_PROMOTION_LINKS],
)
async def post_promotion_links(body: PromotionLinkCreate, session: SessionDep) -> dict[str, Any]:
    """选短剧，按 IAA/中额/小额/超小额/超超小额填 URL；剧场按 IAA/IAP 自动挂应用。"""
    return success(await create_promotion_links(session, body))


@router.patch(
    "/promotion-links/{link_id}",
    response_model=Envelope[PromotionLinkItem],
    summary="编辑端原生推广链",
    dependencies=[_PROMOTION_LINKS],
)
async def patch_promotion_link(link_id: int, body: PromotionLinkUpdate, session: SessionDep) -> dict[str, Any]:
    """剧名不可改，其它字段只改传了的。"""
    return success(await update_promotion_link(session, link_id, body))

