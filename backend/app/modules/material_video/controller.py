"""视频素材 HTTP。不在接口层做菜单鉴权，只认登录态。"""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import require_token
from app.core.db import get_session
from app.core.envelope import Envelope, success
from app.modules.material_video.schema import VideoCreate, VideoItem
from app.modules.material_video.service import create_video

router = APIRouter(prefix="/api/v1/material", tags=["material"])

SessionDep = Annotated[AsyncSession, Depends(get_session)]
PrincipalDep = Annotated[dict[str, Any], Depends(require_token)]


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
