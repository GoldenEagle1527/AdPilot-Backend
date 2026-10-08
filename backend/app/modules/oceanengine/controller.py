"""巨量账户、授权、项目、上传、报表与关停 HTTP。"""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile
from sqlalchemy import select

from app.core.envelope import ApiError, Envelope, success
from app.core.pagination import PageData
from app.modules.account.api import router as account_router
from app.modules.account.commands import assert_oauth_state, choose_library
from app.modules.account.model import ProductLibrary
from app.modules.oceanengine.schema import (
    AdvertiserItem,
    AdvertiserQuery,
    AuthorizeData,
    AuthorizeQuery,
    AutoPauseBody,
    AutoPauseResult,
    ImageItem,
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
    upload_image,
    upload_product,
    upload_video,
)
from app.modules.system_admin import require_menu
from app.modules.system_admin.deps import SessionDep
from app.modules.system_admin.domain.access import effective_menu_ids, user_by_login

router = APIRouter(prefix="/api/v1/oceanengine", tags=["oceanengine"])

Menu32 = Annotated[dict[str, Any], Depends(require_menu("32"))]
Menu64 = Annotated[dict[str, Any], Depends(require_menu("64"))]
MenuAdvertiser = Annotated[dict[str, Any], Depends(require_menu("63", "32"))]


async def _granted_menu_ids(session: SessionDep, principal: dict[str, Any]) -> set[str]:
    granted = principal.get("menu_ids")
    enabled = principal.get("enabled")
    if isinstance(granted, list) and enabled is not None:
        if enabled is False:
            raise ApiError(403, "已登录但无对应菜单或组件")
        return {str(item) for item in granted}
    user = await user_by_login(session, str(principal["login_account"]))
    if user is None or not user.enabled:
        raise ApiError(403, "已登录但无对应菜单或组件")
    return {str(item) for item in await effective_menu_ids(session, user)}


async def _advertiser_only_user_id(session: SessionDep, principal: dict[str, Any]) -> int | None:
    """有菜单 63 看全部。只有 32 时用登录账号查出的用户 id 限制名单。"""
    if "63" in await _granted_menu_ids(session, principal):
        return None
    user = await user_by_login(session, str(principal["login_account"]))
    if user is None or not user.enabled:
        raise ApiError(403, "已登录但无对应菜单或组件")
    return user.id


async def _assert_upload_library(
    session: SessionDep, principal: dict[str, Any], library_id: int
) -> None:
    """path 上的库必须是该投手这次该写入的标准库或兜底库。"""
    library = await session.get(ProductLibrary, library_id)
    if library is None or library.is_deleted:
        return
    user = await user_by_login(session, str(principal["login_account"]))
    if user is None or not user.enabled:
        raise ApiError(403, "已登录但无对应菜单或组件")
    chosen = await choose_library(
        session, user.id, library.organization_id, library.library_kind
    )
    if chosen != library.id:
        raise ApiError(409, "商品库不是本次应写入的库")


@router.get(
    "/organizations",
    response_model=Envelope[OrganizationList],
    summary="授权组织列表",
)
async def get_organizations(session: SessionDep, _principal: Menu64) -> dict[str, Any]:
    """列出授权组织，不分页。"""
    data = {"items": await list_organizations(session)}
    await session.commit()
    return success(data)


@router.get(
    "/advertisers",
    response_model=Envelope[PageData[AdvertiserItem]],
    summary="分页查询广告主",
)
async def get_advertisers(
    session: SessionDep,
    principal: MenuAdvertiser,
    query: Annotated[AdvertiserQuery, Query()],
) -> dict[str, Any]:
    """有菜单 63 看全部含失效户；只有 32 时 only_user_id 为当前用户。"""
    only_user_id = await _advertiser_only_user_id(session, principal)
    scoped = query.model_copy(update={"only_user_id": only_user_id})
    data = await list_advertisers(session, scoped)
    await session.commit()
    return success(data)


@router.get(
    "/oauth/authorize",
    response_model=Envelope[AuthorizeData],
    summary="巨量授权链接",
)
async def get_authorize(
    session: SessionDep,
    _principal: Menu64,
    query: Annotated[AuthorizeQuery, Query()],
) -> dict[str, Any]:
    """按 third 或 self 返回授权页地址。"""
    url = await authorize_url(session, query.channel)
    await session.commit()
    return success({"authorize_url": url})


@router.get(
    "/oauth/callback",
    response_model=Envelope[OAuthTokenData],
    summary="巨量授权回调",
)
async def get_oauth_callback(
    session: SessionDep,
    query: Annotated[OAuthCallbackQuery, Query()],
) -> dict[str, Any]:
    """免登录。state 为空仍允许；非空必须用 jwt_secret 验 HMAC。"""
    if query.state:
        await assert_oauth_state(session, query.state)
    data = await oauth_callback(session, query.auth_code, query.state)
    await session.commit()
    return success(data)


@router.post(
    "/projects",
    response_model=Envelope[ProjectItem],
    summary="创建项目",
)
async def post_project(
    session: SessionDep,
    _principal: Menu32,
    body: ProjectCreate,
) -> dict[str, Any]:
    """创建巨量项目。"""
    data = await create_project(session, body)
    await session.commit()
    return success(data)


@router.post(
    "/videos",
    response_model=Envelope[VideoItem],
    summary="上传视频",
)
async def post_video(
    session: SessionDep,
    _principal: Menu32,
    body: VideoCreate,
) -> dict[str, Any]:
    """按视频地址登记素材。"""
    data = await upload_video(session, body)
    await session.commit()
    return success(data)


@router.post(
    "/products",
    response_model=Envelope[ProductItem],
    summary="商品库上传",
)
async def post_product(
    session: SessionDep,
    principal: Menu32,
    body: ProductCreate,
) -> dict[str, Any]:
    """按 library_no 追加一条剧。库必须是 choose_library 选出的那一个。"""
    library = await session.scalar(
        select(ProductLibrary).where(
            ProductLibrary.library_no == body.library_no,
            ProductLibrary.is_deleted == 0,
        )
    )
    if library is None:
        raise ApiError(404, "商品库不存在")
    await _assert_upload_library(session, principal, library.id)
    data = await upload_product(session, body)
    await session.commit()
    return success(data)


@router.post(
    "/images",
    response_model=Envelope[ImageItem],
    summary="上传产品主图",
)
async def post_image(
    session: SessionDep,
    _principal: Menu32,
    advertiser_id: Annotated[int, Form()],
    image_file: Annotated[UploadFile, File()],
) -> dict[str, Any]:
    """本地文件上传。不收图片 URL。"""
    content = await image_file.read()
    data = await upload_image(session, advertiser_id, image_file.filename or "image", content)
    await session.commit()
    return success(data)


@router.get(
    "/reports",
    response_model=Envelope[ReportList],
    summary="自定义报表",
)
async def get_reports(session: SessionDep, _principal: Menu32) -> dict[str, Any]:
    """广告消耗与回收率，不分页。"""
    data = {"items": await list_reports(session)}
    await session.commit()
    return success(data)


@router.post(
    "/promotions/status",
    response_model=Envelope[PromotionStatusList],
    summary="更新广告状态",
)
async def post_promotion_status(
    session: SessionDep,
    _principal: Menu32,
    body: PromotionStatusBody,
) -> dict[str, Any]:
    """批量暂停或启用广告。"""
    data = {"items": await update_promotions(session, body)}
    await session.commit()
    return success(data)


@router.post(
    "/auto-pause/run",
    response_model=Envelope[AutoPauseResult],
    summary="按阈值自动关停",
)
async def post_auto_pause(
    session: SessionDep,
    _principal: Menu32,
    body: AutoPauseBody,
) -> dict[str, Any]:
    """用报表判断并暂停命中的广告。"""
    data = await run_auto_pause(session, body)
    await session.commit()
    return success(data)


router.include_router(account_router)
