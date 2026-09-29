"""三方剧场 HTTP。不在接口层做菜单鉴权，只认登录态。"""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import require_token
from app.core.db import get_session
from app.core.envelope import Envelope, success
from app.core.pagination import PageData
from app.modules.theater.schema import (
    AppCreate,
    AppItem,
    AppQuery,
    AppStatusUpdate,
    PlatformItem,
    PlatformQuery,
    PlatformUpdate,
    PromotionLinkItem,
    PromotionLinkQuery,
    PromotionLinkUpdate,
    PromotionTaskItem,
    PromotionTaskQuery,
)
from app.modules.theater.service import (
    create_app,
    list_apps,
    list_platforms,
    list_promotion_links,
    list_promotion_tasks,
    set_app_status,
    update_platform,
    update_promotion_link,
)

router = APIRouter(prefix="/api/v1/theater", tags=["theater"], dependencies=[Depends(require_token)])

SessionDep = Annotated[AsyncSession, Depends(get_session)]


@router.get(
    "/platforms",
    response_model=Envelope[PageData[PlatformItem]],
    summary="分页查询平台",
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
)
async def post_app(body: AppCreate, session: SessionDep) -> dict[str, Any]:
    """新增一条有效应用。平台须启用且支持所选剧场类型，同平台剧场名称不重复。"""
    return success(await create_app(session, body))


@router.patch(
    "/apps/{app_id}/status",
    response_model=Envelope[AppItem],
    summary="改应用状态",
)
async def patch_app_status(app_id: int, body: AppStatusUpdate, session: SessionDep) -> dict[str, Any]:
    """列表里切换有效/无效，只改状态。"""
    return success(await set_app_status(session, app_id, body))


@router.get(
    "/promotion-tasks",
    response_model=Envelope[PageData[PromotionTaskItem]],
    summary="分页查询推广链同步任务",
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
)
async def get_promotion_links(
    session: SessionDep,
    query: Annotated[PromotionLinkQuery, Query()],
) -> dict[str, Any]:
    """按首发日期段、剧场、剧名、启用状态筛选推广链，按创建时间倒序。"""
    return success(await list_promotion_links(session, query))


@router.patch(
    "/promotion-links/{link_id}",
    response_model=Envelope[PromotionLinkItem],
    summary="编辑端原生推广链",
)
async def patch_promotion_link(link_id: int, body: PromotionLinkUpdate, session: SessionDep) -> dict[str, Any]:
    """剧名不可改，其它字段只改传了的。"""
    return success(await update_promotion_link(session, link_id, body))

