"""巨量账户、授权、项目、上传、报表与关停 HTTP。"""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query

from app.core.envelope import Envelope, success
from app.core.pagination import PageData
from app.modules.oceanengine.schema import (
    AdvertiserItem,
    AdvertiserQuery,
    AuthorizeData,
    AuthorizeQuery,
    AutoPauseBody,
    AutoPauseResult,
    OAuthCallbackQuery,
    OAuthTokenData,
    OrganizationList,
    ProductCreate,
    ProductItem,
    ProjectCreate,
    ProjectItem,
    PromotionStatusBody,
    PromotionStatusList,
    ReportList,
    VideoCreate,
    VideoItem,
)
from app.modules.oceanengine.service import (
    authorize_url,
    create_project,
    list_advertisers,
    list_organizations,
    list_reports,
    oauth_callback,
    run_auto_pause,
    update_promotions,
    upload_product,
    upload_video,
)
from app.modules.system_admin import require_menu

router = APIRouter(prefix="/api/v1/oceanengine", tags=["oceanengine"])

PrincipalDep = Annotated[dict[str, Any], Depends(require_menu("32"))]


@router.get(
    "/organizations",
    response_model=Envelope[OrganizationList],
    summary="授权组织列表",
)
async def get_organizations(_principal: PrincipalDep) -> dict[str, Any]:
    """列出授权组织，不分页。"""
    return success({"items": await list_organizations()})


@router.get(
    "/advertisers",
    response_model=Envelope[PageData[AdvertiserItem]],
    summary="分页查询广告主",
)
async def get_advertisers(
    _principal: PrincipalDep,
    query: Annotated[AdvertiserQuery, Query()],
) -> dict[str, Any]:
    """按名称或账户 id 分页列出广告主。"""
    return success(await list_advertisers(query))


@router.get(
    "/oauth/authorize",
    response_model=Envelope[AuthorizeData],
    summary="巨量授权链接",
)
async def get_authorize(
    _principal: PrincipalDep,
    query: Annotated[AuthorizeQuery, Query()],
) -> dict[str, Any]:
    """按 third 或 self 返回授权页地址。"""
    return success({"authorize_url": authorize_url(query.channel)})


@router.get(
    "/oauth/callback",
    response_model=Envelope[OAuthTokenData],
    summary="巨量授权回调",
)
async def get_oauth_callback(
    _principal: PrincipalDep,
    query: Annotated[OAuthCallbackQuery, Query()],
) -> dict[str, Any]:
    """用 auth_code 换 access_token。"""
    return success(await oauth_callback(query.auth_code, query.state))


@router.post(
    "/projects",
    response_model=Envelope[ProjectItem],
    summary="创建项目",
)
async def post_project(
    _principal: PrincipalDep,
    body: ProjectCreate,
) -> dict[str, Any]:
    """创建巨量项目。"""
    return success(await create_project(body))


@router.post(
    "/videos",
    response_model=Envelope[VideoItem],
    summary="上传视频",
)
async def post_video(
    _principal: PrincipalDep,
    body: VideoCreate,
) -> dict[str, Any]:
    """按视频地址登记素材。"""
    return success(await upload_video(body))


@router.post(
    "/product-libraries/{library_id}/products",
    response_model=Envelope[ProductItem],
    summary="商品库上传",
)
async def post_product(
    library_id: int,
    _principal: PrincipalDep,
    body: ProductCreate,
) -> dict[str, Any]:
    """向商品库追加一条剧。"""
    return success(await upload_product(library_id, body))


@router.get(
    "/reports",
    response_model=Envelope[ReportList],
    summary="自定义报表",
)
async def get_reports(_principal: PrincipalDep) -> dict[str, Any]:
    """广告消耗与回收率，不分页。"""
    return success({"items": await list_reports()})


@router.post(
    "/promotions/status",
    response_model=Envelope[PromotionStatusList],
    summary="更新广告状态",
)
async def post_promotion_status(
    _principal: PrincipalDep,
    body: PromotionStatusBody,
) -> dict[str, Any]:
    """批量暂停或启用广告。"""
    return success({"items": await update_promotions(body)})


@router.post(
    "/auto-pause/run",
    response_model=Envelope[AutoPauseResult],
    summary="按阈值自动关停",
)
async def post_auto_pause(
    _principal: PrincipalDep,
    body: AutoPauseBody,
) -> dict[str, Any]:
    """用报表判断并暂停命中的广告。"""
    return success(await run_auto_pause(body))
