from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.envelope import ApiError, Envelope, success
from app.core.pagination import PageData, PageParams, page_data, page_params
from app.modules.system_admin.deps import MENU_ROLES, SessionDep, require_menu
from app.modules.system_admin.domain.access import publish_acl_for_users, user_ids_holding_role
from app.modules.system_admin.domain.models import Department, DepartmentRole, Role, User, UserRole
from app.modules.system_admin.domain.org import department_not_deleted, user_not_deleted
from app.modules.system_admin.schemas.common import AssignedUser, IdEnabled, RoleName
from app.modules.system_admin.schemas.roles import (
    CreateRoleBody,
    RoleListItem,
    SetRoleStatusBody,
    UpdateRoleBody,
    role_item_dict,
)

router = APIRouter(prefix="/api/v1/system-admin", tags=["system-admin"])

PrincipalDep = Annotated[dict[str, str], Depends(require_menu(MENU_ROLES))]


def _role_filters(name: str | None, enabled: bool | None):
    filters = []
    if name:
        filters.append(Role.name.ilike(f"%{name}%"))
    if enabled is not None:
        filters.append(Role.enabled.is_(enabled))
    return filters


async def _assignments(
    session: AsyncSession, role_ids: list[str]
) -> tuple[dict[str, list[AssignedUser]], dict[str, list[RoleName]]]:
    users_map: dict[str, list[AssignedUser]] = defaultdict(list)
    depts_map: dict[str, list[RoleName]] = defaultdict(list)
    if not role_ids:
        return users_map, depts_map
    user_rows = (
        await session.execute(
            select(UserRole.role_id, User.id, User.login_account, User.nickname)
            .join(User, User.id == UserRole.user_id)
            .where(UserRole.role_id.in_(role_ids), user_not_deleted())
            .order_by(User.login_account, User.id)
        )
    ).all()
    for role_id, user_id, login_account, nickname in user_rows:
        users_map[str(role_id)].append(
            AssignedUser(id=str(user_id), login_account=login_account, nickname=nickname)
        )
    dept_rows = (
        await session.execute(
            select(DepartmentRole.role_id, Department.id, Department.name)
            .join(Department, Department.id == DepartmentRole.department_id)
            .where(DepartmentRole.role_id.in_(role_ids), department_not_deleted())
            .order_by(Department.name, Department.id)
        )
    ).all()
    for role_id, dept_id, dept_name in dept_rows:
        depts_map[str(role_id)].append(RoleName(id=str(dept_id), name=dept_name))
    return users_map, depts_map


async def _role_payload(session: AsyncSession, role: Role) -> dict[str, Any]:
    users_map, depts_map = await _assignments(session, [str(role.id)])
    return role_item_dict(role, users_map.get(str(role.id), []), depts_map.get(str(role.id), []))


async def _get_role_or_404(session: AsyncSession, role_id: str) -> Role:
    role = await session.get(Role, role_id)
    if role is None:
        raise ApiError(404, "NOT_FOUND", "角色不存在")
    return role


def _touch(role: Role, login_account: str) -> None:
    role.updated_by = login_account
    role.updated_at = datetime.now(timezone.utc)


@router.get("/roles", response_model=Envelope[PageData[RoleListItem]])
async def list_roles(
    session: SessionDep,
    _principal: PrincipalDep,
    params: Annotated[PageParams, Depends(page_params)],
    name: str | None = Query(default=None),
    enabled: bool | None = Query(default=None),
):
    filters = _role_filters(name, enabled)
    stmt = select(Role)
    count_stmt = select(func.count()).select_from(Role)
    if filters:
        stmt = stmt.where(*filters)
        count_stmt = count_stmt.where(*filters)
    total = int(await session.scalar(count_stmt) or 0)
    stmt = (
        stmt.order_by(Role.created_at.desc(), Role.id.desc())
        .offset(params.offset)
        .limit(params.page_size)
    )
    roles = list((await session.execute(stmt)).scalars().all())
    users_map, depts_map = await _assignments(session, [role.id for role in roles])
    items = [
        role_item_dict(role, users_map.get(str(role.id), []), depts_map.get(str(role.id), []))
        for role in roles
    ]
    return success(page_data(items, total, params))


@router.post("/roles", response_model=Envelope[RoleListItem])
async def create_role(
    body: CreateRoleBody,
    session: SessionDep,
    principal: PrincipalDep,
):
    role = Role(
        name=body.name,
        remark=body.remark,
        enabled=True,
        updated_by=principal["login_account"],
    )
    session.add(role)
    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        raise ApiError(422, "VALIDATION_ERROR", "name: 角色名已存在")
    await session.refresh(role)
    return success(role_item_dict(role, [], []))


@router.put("/roles/{role_id}", response_model=Envelope[RoleListItem])
async def update_role(
    role_id: str,
    body: UpdateRoleBody,
    session: SessionDep,
    principal: PrincipalDep,
):
    role = await _get_role_or_404(session, role_id)
    role.name = body.name
    if "remark" in body.model_fields_set:
        role.remark = body.remark
    _touch(role, principal["login_account"])
    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        raise ApiError(422, "VALIDATION_ERROR", "name: 角色名已存在")
    await session.refresh(role)
    return success(await _role_payload(session, role))


@router.patch("/roles/{role_id}/status", response_model=Envelope[IdEnabled])
async def set_role_status(
    role_id: str,
    body: SetRoleStatusBody,
    session: SessionDep,
    principal: PrincipalDep,
):
    role = await _get_role_or_404(session, role_id)
    role.enabled = body.enabled
    _touch(role, principal["login_account"])
    await session.commit()
    await publish_acl_for_users(session, await user_ids_holding_role(session, role.id))
    return success({"id": str(role.id), "enabled": role.enabled})
