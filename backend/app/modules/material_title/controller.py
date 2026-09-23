"""素材标题 HTTP。不在接口层做菜单鉴权，只认登录态；用户只碰得到自己的标题。"""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import require_token
from app.core.db import get_session
from app.core.envelope import Envelope, success
from app.core.pagination import PageData
from app.modules.material_title.schema import (
    TitleBatchCreate,
    TitleBatchCreated,
    TitleItem,
    TitleQuery,
    TitleUpdate,
)
from app.modules.material_title.service import batch_create_titles, list_titles, update_title

router = APIRouter(prefix="/api/v1/material", tags=["material"])

SessionDep = Annotated[AsyncSession, Depends(get_session)]
PrincipalDep = Annotated[dict[str, Any], Depends(require_token)]


@router.get(
    "/titles",
    response_model=Envelope[PageData[TitleItem]],
    summary="分页查询标题",
)
async def get_titles(
    session: SessionDep,
    principal: PrincipalDep,
    query: Annotated[TitleQuery, Query()],
) -> dict[str, Any]:
    """按分类和标题名分页列出自己上传的标题。"""
    return success(await list_titles(session, query, int(principal["id"])))


@router.post(
    "/titles",
    response_model=Envelope[TitleBatchCreated],
    summary="批量添加标题",
)
async def create_titles(
    body: TitleBatchCreate,
    session: SessionDep,
    principal: PrincipalDep,
) -> dict[str, Any]:
    """一个分类下批量新增标题，上传者取当前登录用户。"""
    return success(await batch_create_titles(session, body, int(principal["id"])))


@router.patch(
    "/titles/{title_id}",
    response_model=Envelope[TitleItem],
    summary="改标题名和分类",
)
async def patch_title(
    title_id: int,
    body: TitleUpdate,
    session: SessionDep,
    principal: PrincipalDep,
) -> dict[str, Any]:
    """只改标题名和分类，且只能改自己上传的那条。"""
    return success(await update_title(session, title_id, body, int(principal["id"])))
