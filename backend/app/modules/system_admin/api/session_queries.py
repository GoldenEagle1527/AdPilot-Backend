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
from app.modules.system_admin.domain.models import MenuNode, UserDataScope
from app.modules.system_admin.schemas.session import SessionDataScope, SessionMe, SessionMenus

router = APIRouter(prefix="/api/v1/system-admin", tags=["system-admin"])

PrincipalDep = Annotated[dict[str, str], Depends(current_principal)]


async def _require_local_user(session, principal: dict[str, str]):
    user = await user_by_login(session, principal["login_account"])
    if user is None or not user.enabled:
        raise ApiError(403, "FORBIDDEN", "已登录但无对应本地用户")
    return user


@router.get("/session/me", response_model=Envelope[SessionMe])
async def get_session_me(session: SessionDep, principal: PrincipalDep) -> dict:
    user = await _require_local_user(session, principal)
    dept_name = user.department.name if user.department is not None else ""
    payload = SessionMe(
        id=user.id,
        nickname=user.nickname,
        login_account=user.login_account,
        short_name=user.short_name,
        phone=user.phone,
        enabled=user.enabled,
        department_id=user.department_id,
        department_name=dept_name,
        role_kind=user.role_kind,
        tenant=user.tenant,
        remark=user.remark,
    )
    return success(payload.model_dump())


@router.get("/session/menus", response_model=Envelope[SessionMenus])
async def get_session_menus(session: SessionDep, principal: PrincipalDep) -> dict:
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


@router.get("/session/data-scope", response_model=Envelope[SessionDataScope])
async def get_session_data_scope(session: SessionDep, principal: PrincipalDep) -> dict:
    user = await _require_local_user(session, principal)
    rows = await session.execute(
        select(UserDataScope.department_id)
        .where(UserDataScope.user_id == user.id)
        .order_by(UserDataScope.department_id)
    )
    return success(SessionDataScope(department_ids=[row[0] for row in rows.all()]).model_dump())
