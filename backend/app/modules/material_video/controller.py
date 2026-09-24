"""视频素材 HTTP。不在接口层做菜单鉴权，只认登录态。"""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import require_token
from app.core.db import get_session
from app.core.envelope import Envelope, success
from app.core.pagination import PageData
from app.modules.material_video.schema import (
    BatchDeleted,
    BatchPitcherBody,
    BatchPublic,
    BatchShareBody,
    BatchUserIds,
    OwnershipChange,
    OwnershipChanged,
    PitcherChange,
    PitcherChanged,
    ShareChange,
    ShareChanged,
    TagItem,
    TagQuery,
    VideoCreate,
    VideoDeleted,
    VideoIdsBody,
    VideoItem,
    VideoQuery,
)
from app.modules.material_video.service import (
    batch_assign_pitchers,
    batch_delete_videos,
    batch_make_public,
    batch_share_videos,
    change_ownership,
    change_pitchers,
    change_shares,
    create_video,
    delete_video,
    list_tags,
    list_videos,
)

router = APIRouter(prefix="/api/v1/material", tags=["material"])

SessionDep = Annotated[AsyncSession, Depends(get_session)]
PrincipalDep = Annotated[dict[str, Any], Depends(require_token)]


@router.get(
    "/video-tags",
    response_model=Envelope[PageData[TagItem]],
    summary="分页查询视频标签",
)
async def get_video_tags(
    session: SessionDep,
    principal: PrincipalDep,
    query: Annotated[TagQuery, Query()],
) -> dict[str, Any]:
    """按名称模糊列出当前用户能看见的素材标签。"""
    return success(await list_tags(session, query, int(principal["id"])))


@router.get(
    "/videos",
    response_model=Envelope[PageData[VideoItem]],
    summary="分页查询视频素材",
)
async def get_videos(
    session: SessionDep,
    principal: PrincipalDep,
    query: Annotated[VideoQuery, Query()],
) -> dict[str, Any]:
    """按可见范围和筛选条件分页列出视频素材。"""
    return success(await list_videos(session, query, int(principal["id"])))


@router.post(
    "/videos",
    response_model=Envelope[VideoItem],
    summary="添加视频素材",
)
async def post_video(
    body: VideoCreate,
    session: SessionDep,
    principal: PrincipalDep,
) -> dict[str, Any]:
    """新增一条视频素材，上传者取当前登录用户。"""
    return success(await create_video(session, body, int(principal["id"])))


@router.delete(
    "/videos/{video_id}",
    response_model=Envelope[VideoDeleted],
    summary="删除视频素材",
)
async def delete_one_video(
    video_id: int,
    session: SessionDep,
    principal: PrincipalDep,
) -> dict[str, Any]:
    """软删当前用户自己上传的一条视频素材。别人的按不存在处理。"""
    return success(await delete_video(session, video_id, int(principal["id"])))


@router.post(
    "/videos/{video_id}/shares",
    response_model=Envelope[ShareChanged],
    summary="添加或取消视频素材共享",
)
async def post_video_shares(
    video_id: int,
    body: ShareChange,
    session: SessionDep,
    principal: PrincipalDep,
) -> dict[str, Any]:
    """上传者一次添加和取消共享。取消后，这个人分过的投手还在。"""
    return success(await change_shares(session, video_id, body, int(principal["id"])))


@router.post(
    "/videos/{video_id}/pitchers",
    response_model=Envelope[PitcherChanged],
    summary="添加或取消视频素材的投手",
)
async def post_video_pitchers(
    video_id: int,
    body: PitcherChange,
    session: SessionDep,
    principal: PrincipalDep,
) -> dict[str, Any]:
    """上传者或共享人一次添加和取消自己分出去的投手。"""
    return success(await change_pitchers(session, video_id, body, int(principal["id"])))


@router.post(
    "/videos/{video_id}/ownership",
    response_model=Envelope[OwnershipChanged],
    summary="修改视频素材归属",
)
async def post_video_ownership(
    video_id: int,
    body: OwnershipChange,
    session: SessionDep,
    principal: PrincipalDep,
) -> dict[str, Any]:
    """把自己上传的一条视频改成公有或私有。"""
    return success(await change_ownership(session, video_id, body, int(principal["id"])))


@router.post(
    "/videos/batch-delete",
    response_model=Envelope[BatchDeleted],
    summary="批量删除视频素材",
)
async def post_batch_delete_videos(
    body: VideoIdsBody,
    session: SessionDep,
    principal: PrincipalDep,
) -> dict[str, Any]:
    """软删自己上传的多条视频。有一条不是自己的就整批不删。"""
    return success(await batch_delete_videos(session, body, int(principal["id"])))


@router.post(
    "/videos/batch-shares",
    response_model=Envelope[BatchUserIds],
    summary="批量共享视频素材",
)
async def post_batch_share_videos(
    body: BatchShareBody,
    session: SessionDep,
    principal: PrincipalDep,
) -> dict[str, Any]:
    """把同一批人加到自己的多条素材上。不取消原有共享。"""
    return success(await batch_share_videos(session, body, int(principal["id"])))


@router.post(
    "/videos/batch-public",
    response_model=Envelope[BatchPublic],
    summary="批量把视频素材转为公有",
)
async def post_batch_public_videos(
    body: VideoIdsBody,
    session: SessionDep,
    principal: PrincipalDep,
) -> dict[str, Any]:
    """把自己上传的多条视频改成公有。"""
    return success(await batch_make_public(session, body, int(principal["id"])))


@router.post(
    "/videos/batch-pitchers",
    response_model=Envelope[BatchUserIds],
    summary="批量设置视频素材的投手归属",
)
async def post_batch_pitcher_videos(
    body: BatchPitcherBody,
    session: SessionDep,
    principal: PrincipalDep,
) -> dict[str, Any]:
    """把同一批投手加到多条素材上，记在当前用户名下。"""
    return success(await batch_assign_pitchers(session, body, int(principal["id"])))
