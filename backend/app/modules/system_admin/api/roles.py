from __future__ import annotations

from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.envelope import ApiError, Envelope, success
from app.core.pagination import PageData, PageParams, page_data, page_params
from app.modules.system_admin.deps import MENU_ROLES, SessionDep, require_menu
from app.modules.system_admin.domain.models import DepartmentRole, Role, UserRole
from app.modules.system_admin.schemas.common import IdEnabled
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


async def _role_counts(session: AsyncSession, role_id: str) -> tuple[int, int]:
    user_n = await session.scalar(
        select(func.count()).select_from(UserRole).where(UserRole.role_id == role_id)
    )
    dept_n = await session.scalar(
        select(func.count()).select_from(DepartmentRole).where(DepartmentRole.role_id == role_id)
    )
    return int(user_n or 0), int(dept_n or 0)


async def _get_role_or_404(session: AsyncSession, role_id: str) -> Role:
    role = await session.get(Role, role_id)
    if role is None:
        raise ApiError(404, "NOT_FOUND", "角色不存在")
    return role


@router.get("/roles", response_model=Envelope[PageData[RoleListItem]])
async def list_roles(
    session: SessionDep,
    _principal: PrincipalDep,
    params: Annotated[PageParams, Depends(page_params)],
    name: str | None = Query(default=None),
    enabled: bool | None = Query(default=None),
):
    filters = _role_filters(name, enabled)
    user_sq = (
        select(UserRole.role_id, func.count().label("cnt"))
        .group_by(UserRole.role_id)
        .subquery()
    )
    dept_sq = (
        select(DepartmentRole.role_id, func.count().label("cnt"))
        .group_by(DepartmentRole.role_id)
        .subquery()
    )
    stmt = (
        select(
            Role,
            func.coalesce(user_sq.c.cnt, 0),
            func.coalesce(dept_sq.c.cnt, 0),
        )
        .outerjoin(user_sq, user_sq.c.role_id == Role.id)
        .outerjoin(dept_sq, dept_sq.c.role_id == Role.id)
    )
    if filters:
        stmt = stmt.where(*filters)
    count_stmt = select(func.count()).select_from(Role)
    if filters:
        count_stmt = count_stmt.where(*filters)
    total = int(await session.scalar(count_stmt) or 0)
    stmt = (
        stmt.order_by(Role.created_at.desc(), Role.id.desc())
        .offset(params.offset)
        .limit(params.page_size)
    )
    rows = (await session.execute(stmt)).all()
    items = [
        role_item_dict(role, int(user_c), int(dept_c)) for role, user_c, dept_c in rows
    ]
    return success(page_data(items, total, params))


@router.post("/roles", response_model=Envelope[RoleListItem])
async def create_role(
    body: CreateRoleBody,
    session: SessionDep,
    _principal: PrincipalDep,
):
    role = Role(name=body.name, remark=body.remark, enabled=True)
    session.add(role)
    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        raise ApiError(422, "VALIDATION_ERROR", "name: 角色名已存在")
    await session.refresh(role)
    return success(role_item_dict(role, 0, 0))


@router.put("/roles/{role_id}", response_model=Envelope[RoleListItem])
async def update_role(
    role_id: str,
    body: UpdateRoleBody,
    session: SessionDep,
    _principal: PrincipalDep,
):
    role = await _get_role_or_404(session, role_id)
    role.name = body.name
    if "remark" in body.model_fields_set:
        role.remark = body.remark
    role.updated_at = datetime.now(timezone.utc)
    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        raise ApiError(422, "VALIDATION_ERROR", "name: 角色名已存在")
    await session.refresh(role)
    user_c, dept_c = await _role_counts(session, role.id)
    return success(role_item_dict(role, user_c, dept_c))


@router.patch("/roles/{role_id}/status", response_model=Envelope[IdEnabled])
async def set_role_status(
    role_id: str,
    body: SetRoleStatusBody,
    session: SessionDep,
    _principal: PrincipalDep,
):
    role = await _get_role_or_404(session, role_id)
    role.enabled = body.enabled
    role.updated_at = datetime.now(timezone.utc)
    await session.commit()
    return success({"id": role.id, "enabled": role.enabled})
