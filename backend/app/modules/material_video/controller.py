"""视频素材 HTTP。不在接口层做菜单鉴权，只认登录态。"""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import require_token
from app.core.db import get_session
from app.core.envelope import Envelope, success
from app.core.pagination import PageData
from app.modules.material_video.schema import TagItem, TagQuery, VideoCreate, VideoItem, VideoQuery
from app.modules.material_video.service import create_video, list_tags, list_videos

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
