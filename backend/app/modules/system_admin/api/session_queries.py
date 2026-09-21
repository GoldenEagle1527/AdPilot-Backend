"""登录会话侧查询：当前用户、有效菜单、有效数据范围。"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import select

from app.core.envelope import ApiError, Envelope, success
from app.modules.system_admin.deps import SessionDep, current_principal
from app.modules.system_admin.domain.access import (
    build_menu_tree,
    effective_menu_ids,
    user_by_login,
)
from app.modules.system_admin.domain.models import MenuNode
from app.modules.system_admin.domain.org import effective_data_scope
from app.modules.system_admin.schemas.session import SessionDataScope, SessionMe, SessionMenus

router = APIRouter(prefix="/api/v1/system-admin", tags=["system-admin"])

PrincipalDep = Annotated[dict[str, str], Depends(current_principal)]


async def _require_local_user(session, principal: dict[str, str]):
    user = await user_by_login(session, principal["login_account"])
    if user is None or not user.enabled:
        raise ApiError(403, "FORBIDDEN", "已登录但无对应本地用户")
    return user


@router.get("/session/me", response_model=Envelope[SessionMe], summary="当前用户主档")
async def get_session_me(session: SessionDep, principal: PrincipalDep) -> dict:
    """返回当前登录账号对应的本地用户主档。"""
    user = await _require_local_user(session, principal)
    dept_name = user.department.name if user.department is not None else ""
    payload = SessionMe(
        id=str(user.id),
        nickname=user.nickname,
        login_account=user.login_account,
        short_name=user.short_name,
        phone=user.phone,
        enabled=user.enabled,
        department_id=str(user.department_id),
        department_name=dept_name,
        role_kind=user.role_kind,
        tenant=user.tenant,
        remark=user.remark,
    )
    return success(payload.model_dump())


@router.get("/session/menus", response_model=Envelope[SessionMenus], summary="当前用户有效菜单")
async def get_session_menus(session: SessionDep, principal: PrincipalDep) -> dict:
    """按用户有效菜单/组件拼出侧栏树。"""
    user = await _require_local_user(session, principal)
    cached = principal.get("menu_ids")
    if isinstance(cached, list):
        granted = set(cached)
    else:
        granted = await effective_menu_ids(session, user)
    all_nodes = await session.execute(select(MenuNode))
    nodes_by_id = {node.id: node for node in all_nodes.scalars().all()}
    items = build_menu_tree(nodes_by_id, granted)
    return success(SessionMenus(items=items).model_dump())


@router.get(
    "/session/data-scope",
    response_model=Envelope[SessionDataScope],
    summary="当前用户有效数据范围",
)
async def get_session_data_scope(session: SessionDep, principal: PrincipalDep) -> dict:
    """返回有效部门范围；空列表且 self_only 表示仅本人。"""
    user = await _require_local_user(session, principal)
    self_only, department_ids = await effective_data_scope(session, user)
    return success(
        SessionDataScope(
            department_ids=department_ids,
            self_only=self_only,
            user_id=str(user.id),
        ).model_dump()
    )
