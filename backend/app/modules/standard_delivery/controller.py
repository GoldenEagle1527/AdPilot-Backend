"""漫剧标准投放 HTTP。免费和付费各用自己的菜单节点。"""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import require_token
from app.core.db import get_session
from app.core.envelope import ApiError, Envelope, success
from app.core.pagination import PageData
from app.modules.standard_delivery.schema import (
    DeletedItem,
    DraftItem,
    DraftQuery,
    DraftWrite,
    RuleItem,
    RuleQuery,
    RuleWrite,
    TemplateItem,
    TemplateQuery,
    TemplateUpdate,
    TemplateWrite,
)
from app.modules.standard_delivery.service import (
    create_draft,
    create_rule,
    create_template,
    delete_draft,
    delete_rule,
    delete_template,
    get_draft,
    get_rule,
    get_template,
    list_drafts,
    list_rules,
    list_templates,
    update_draft,
    update_rule,
    update_template,
)
from app.modules.system_admin.domain.access import effective_menu_ids, user_by_login

router = APIRouter(
    prefix="/api/v1/standard-delivery",
    tags=["standard-delivery"],
    dependencies=[Depends(require_token)],
)

SessionDep = Annotated[AsyncSession, Depends(get_session)]
PrincipalDep = Annotated[dict[str, Any], Depends(require_token)]

# 免费 / 付费菜单。模板 45/50，任务 39/46，自动规则 51/52。
TEMPLATE_MENU = {"IAA": "45", "IAP": "50"}
DRAFT_MENU = {"IAA": "39", "IAP": "46"}
RULE_MENU = {"IAA": "51", "IAP": "52"}

_FORBIDDEN = "已登录但无对应菜单或组件"


async def _granted(session: AsyncSession, principal: dict[str, Any]) -> set[str]:
    """会话里有菜单就用会话，否则按登录账号现查。"""
    granted = principal.get("menu_ids")
    enabled = principal.get("enabled")
    if isinstance(granted, list) and enabled is not None:
        if enabled is False:
            raise ApiError(403, _FORBIDDEN)
        return {str(item) for item in granted}
    user = await user_by_login(session, str(principal["login_account"]))
    if user is None or not user.enabled:
        raise ApiError(403, _FORBIDDEN)
    return {str(item) for item in await effective_menu_ids(session, user)}


async def _allowed(session: AsyncSession, principal: dict[str, Any], mapping: dict[str, str]) -> set[str]:
    """当前用户能操作的收费模式。一个都没有就拒绝。"""
    granted = await _granted(session, principal)
    allowed = {mode for mode, menu_id in mapping.items() if menu_id in granted}
    if not allowed:
        raise ApiError(403, _FORBIDDEN)
    return allowed


def _require_query_mode(allowed: set[str], charge_mode: str) -> None:
    """列表上的收费模式必须落在已授权的菜单里。"""
    if charge_mode not in allowed:
        raise ApiError(403, _FORBIDDEN)


def _user_id(principal: dict[str, Any]) -> int:
    """登录主体上的用户 id。"""
    return int(principal["id"])


@router.get("/templates", response_model=Envelope[PageData[TemplateItem]], summary="分页查询投放模板")
async def get_templates(
    session: SessionDep,
    principal: PrincipalDep,
    query: Annotated[TemplateQuery, Query()],
) -> dict[str, Any]:
    """按收费模式、名称、主体分页列出模板。"""
    _require_query_mode(await _allowed(session, principal, TEMPLATE_MENU), query.charge_mode)
    return success(await list_templates(session, query))


@router.get(
    "/templates/{template_id}",
    response_model=Envelope[TemplateItem],
    summary="查询一条投放模板",
)
async def get_one_template(template_id: int, session: SessionDep, principal: PrincipalDep) -> dict[str, Any]:
    """取一条未删除的模板。"""
    allowed = await _allowed(session, principal, TEMPLATE_MENU)
    return success(await get_template(session, template_id, allowed))


@router.post("/templates", response_model=Envelope[TemplateItem], summary="新增投放模板")
async def post_template(
    body: TemplateWrite, session: SessionDep, principal: PrincipalDep
) -> dict[str, Any]:
    """新增模板。主体须为标准投放，付费模板至少有一条出价面板。"""
    allowed = await _allowed(session, principal, TEMPLATE_MENU)
    return success(await create_template(session, body, allowed))


@router.put(
    "/templates/{template_id}",
    response_model=Envelope[TemplateItem],
    summary="保存投放模板",
)
async def put_template(
    template_id: int, body: TemplateUpdate, session: SessionDep, principal: PrincipalDep
) -> dict[str, Any]:
    """整表保存模板。收费模式不可改。"""
    allowed = await _allowed(session, principal, TEMPLATE_MENU)
    return success(await update_template(session, template_id, body, allowed))


@router.delete(
    "/templates/{template_id}",
    response_model=Envelope[DeletedItem],
    summary="删除投放模板",
)
async def remove_template(template_id: int, session: SessionDep, principal: PrincipalDep) -> dict[str, Any]:
    """软删模板。已被草稿或规则使用时拒绝。"""
    allowed = await _allowed(session, principal, TEMPLATE_MENU)
    return success(await delete_template(session, template_id, allowed))


@router.get(
    "/task-drafts",
    response_model=Envelope[PageData[DraftItem]],
    summary="分页查询投放任务草稿",
)
async def get_task_drafts(
    session: SessionDep,
    principal: PrincipalDep,
    query: Annotated[DraftQuery, Query()],
) -> dict[str, Any]:
    """只列出当前投手自己的草稿。"""
    _require_query_mode(await _allowed(session, principal, DRAFT_MENU), query.charge_mode)
    return success(await list_drafts(session, query, _user_id(principal)))


@router.get(
    "/task-drafts/{draft_id}",
    response_model=Envelope[DraftItem],
    summary="查询一条投放任务草稿",
)
async def get_one_task_draft(draft_id: int, session: SessionDep, principal: PrincipalDep) -> dict[str, Any]:
    """取自己的一条草稿。"""
    allowed = await _allowed(session, principal, DRAFT_MENU)
    return success(await get_draft(session, draft_id, _user_id(principal), allowed))


@router.post("/task-drafts", response_model=Envelope[DraftItem], summary="新增投放任务草稿")
async def post_task_draft(body: DraftWrite, session: SessionDep, principal: PrincipalDep) -> dict[str, Any]:
    """保存草稿。一个抖音号，多个账户共用。不向巨量提交。"""
    allowed = await _allowed(session, principal, DRAFT_MENU)
    return success(await create_draft(session, body, _user_id(principal), allowed))


@router.put(
    "/task-drafts/{draft_id}",
    response_model=Envelope[DraftItem],
    summary="保存投放任务草稿",
)
async def put_task_draft(
    draft_id: int, body: DraftWrite, session: SessionDep, principal: PrincipalDep
) -> dict[str, Any]:
    """整表保存自己的草稿，账户、视频、标题按本次提交替换。"""
    allowed = await _allowed(session, principal, DRAFT_MENU)
    return success(await update_draft(session, draft_id, body, _user_id(principal), allowed))


@router.delete(
    "/task-drafts/{draft_id}",
    response_model=Envelope[DeletedItem],
    summary="删除投放任务草稿",
)
async def remove_task_draft(draft_id: int, session: SessionDep, principal: PrincipalDep) -> dict[str, Any]:
    """软删自己的草稿。"""
    allowed = await _allowed(session, principal, DRAFT_MENU)
    return success(await delete_draft(session, draft_id, _user_id(principal), allowed))


@router.get(
    "/auto-rules",
    response_model=Envelope[PageData[RuleItem]],
    summary="分页查询自动投放规则",
)
async def get_auto_rules(
    session: SessionDep,
    principal: PrincipalDep,
    query: Annotated[RuleQuery, Query()],
) -> dict[str, Any]:
    """只列出当前投手自己的规则。"""
    _require_query_mode(await _allowed(session, principal, RULE_MENU), query.charge_mode)
    return success(await list_rules(session, query, _user_id(principal)))


@router.get(
    "/auto-rules/{rule_id}",
    response_model=Envelope[RuleItem],
    summary="查询一条自动投放规则",
)
async def get_one_auto_rule(rule_id: int, session: SessionDep, principal: PrincipalDep) -> dict[str, Any]:
    """取自己的一条规则。"""
    allowed = await _allowed(session, principal, RULE_MENU)
    return success(await get_rule(session, rule_id, _user_id(principal), allowed))


@router.post("/auto-rules", response_model=Envelope[RuleItem], summary="新增自动投放规则")
async def post_auto_rule(body: RuleWrite, session: SessionDep, principal: PrincipalDep) -> dict[str, Any]:
    """保存规则。只落库，不到点执行，也不调巨量。"""
    allowed = await _allowed(session, principal, RULE_MENU)
    return success(await create_rule(session, body, _user_id(principal), allowed))


@router.put(
    "/auto-rules/{rule_id}",
    response_model=Envelope[RuleItem],
    summary="保存自动投放规则",
)
async def put_auto_rule(
    rule_id: int, body: RuleWrite, session: SessionDep, principal: PrincipalDep
) -> dict[str, Any]:
    """整表保存自己的规则，短剧按本次提交替换。"""
    allowed = await _allowed(session, principal, RULE_MENU)
    return success(await update_rule(session, rule_id, body, _user_id(principal), allowed))


@router.delete(
    "/auto-rules/{rule_id}",
    response_model=Envelope[DeletedItem],
    summary="删除自动投放规则",
)
async def remove_auto_rule(rule_id: int, session: SessionDep, principal: PrincipalDep) -> dict[str, Any]:
    """软删自己的规则。"""
    allowed = await _allowed(session, principal, RULE_MENU)
    return success(await delete_rule(session, rule_id, _user_id(principal), allowed))
