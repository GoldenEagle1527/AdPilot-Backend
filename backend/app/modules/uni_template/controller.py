"""全域模板 HTTP。模板全员可见，抖音号分配只认当前登录投手。"""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import require_token
from app.core.db import get_session
from app.core.envelope import Envelope, success
from app.core.pagination import PageData
from app.modules.uni_template.schema import (
    DeletedItem,
    DouyinAssignResult,
    DouyinAssignWrite,
    TemplateItem,
    TemplateQuery,
    TemplateWrite,
)
from app.modules.uni_template.service import (
    assign_douyin,
    create_template,
    delete_template,
    get_template,
    list_templates,
    update_template,
)

router = APIRouter(
    prefix="/api/v1/uni-templates",
    tags=["uni-templates"],
    dependencies=[Depends(require_token)],
)

SessionDep = Annotated[AsyncSession, Depends(get_session)]
PrincipalDep = Annotated[dict[str, Any], Depends(require_token)]


def _user_id(principal: dict[str, Any]) -> int:
    """登录主体上的用户 id。"""
    return int(principal["id"])


@router.get("", response_model=Envelope[PageData[TemplateItem]], summary="分页查询全域模板")
async def get_templates(
    session: SessionDep,
    principal: PrincipalDep,
    query: Annotated[TemplateQuery, Query()],
) -> dict[str, Any]:
    """列出未删除的全域模板。每个投手看到的是自己分配的抖音号。"""
    return success(await list_templates(session, query, _user_id(principal)))


@router.get(
    "/{template_id}",
    response_model=Envelope[TemplateItem],
    summary="查询一条全域模板",
)
async def get_one_template(
    template_id: int, session: SessionDep, principal: PrincipalDep
) -> dict[str, Any]:
    """取一条未删除的全域模板。"""
    return success(await get_template(session, template_id, _user_id(principal)))


@router.post("", response_model=Envelope[TemplateItem], summary="新增全域模板")
async def post_template(body: TemplateWrite, session: SessionDep) -> dict[str, Any]:
    """新增模板。主体须为全域投放。不分配抖音号。"""
    return success(await create_template(session, body))


@router.put(
    "/{template_id}",
    response_model=Envelope[TemplateItem],
    summary="保存全域模板",
)
async def put_template(
    template_id: int, body: TemplateWrite, session: SessionDep, principal: PrincipalDep
) -> dict[str, Any]:
    """整表保存。不改抖音号分配。"""
    return success(await update_template(session, template_id, body, _user_id(principal)))


@router.delete(
    "/{template_id}",
    response_model=Envelope[DeletedItem],
    summary="删除全域模板",
)
async def remove_template(template_id: int, session: SessionDep) -> dict[str, Any]:
    """软删一条全域模板。"""
    return success(await delete_template(session, template_id))


@router.put(
    "/{template_id}/douyin-accounts",
    response_model=Envelope[DouyinAssignResult],
    summary="分配当前投手的全域抖音号",
)
async def put_template_douyin(
    template_id: int,
    body: DouyinAssignWrite,
    session: SessionDep,
    principal: PrincipalDep,
) -> dict[str, Any]:
    """用请求里的号换掉当前投手在这条模板上的分配。空数组表示清空。"""
    return success(await assign_douyin(session, template_id, body, _user_id(principal)))
