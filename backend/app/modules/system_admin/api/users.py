from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased, selectinload

from app.core.envelope import ApiError, Envelope, success
from app.core.pagination import PageData, PageParams, page_data, page_params
from app.modules.system_admin.deps import MENU_USERS, SessionDep, require_menu
from app.modules.system_admin.domain.models import Department, DepartmentRole, Role, User
from app.modules.system_admin.domain.password import hash_password_or_default
from app.modules.system_admin.schemas.common import IdEnabled, UserListItem
from app.modules.system_admin.schemas.users import (
    CreateUserRequest,
    SetUserStatusRequest,
    UpdateUserRequest,
    iso8601_z,
)

router = APIRouter(prefix="/api/v1/system-admin", tags=["system-admin"])

PrincipalDep = Annotated[dict[str, str], Depends(require_menu(MENU_USERS))]
_USER_LOAD = (
    selectinload(User.tags),
    selectinload(User.roles),
    selectinload(User.data_scope_departments),
    selectinload(User.department),
)


async def get_department(session: AsyncSession, department_id: str) -> Department:
    department = await session.get(Department, department_id)
    if department is None:
        raise ApiError(404, "NOT_FOUND", "部门不存在")
    return department


async def get_user(session: AsyncSession, user_id: str) -> User:
    result = await session.execute(select(User).options(*_USER_LOAD).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None:
        raise ApiError(404, "NOT_FOUND", "用户不存在")
    return user


async def department_roles_by_dept(
    session: AsyncSession, department_ids: list[str]
) -> dict[str, list[Role]]:
    mapping: dict[str, list[Role]] = {dept_id: [] for dept_id in department_ids}
    if not department_ids:
        return mapping
    result = await session.execute(
        select(DepartmentRole.department_id, Role)
        .join(Role, Role.id == DepartmentRole.role_id)
        .where(DepartmentRole.department_id.in_(department_ids))
        .order_by(Role.id)
    )
    for dept_id, role in result.all():
        mapping.setdefault(dept_id, []).append(role)
    return mapping


def _named(items: list) -> list[dict[str, str]]:
    return [{"id": item.id, "name": item.name} for item in items]


def serialize_user(user: User, department_roles: list[Role] | None = None) -> dict:
    roles = department_roles if department_roles is not None else []
    return {
        "id": user.id,
        "nickname": user.nickname,
        "login_account": user.login_account,
        "short_name": user.short_name,
        "phone": user.phone,
        "enabled": user.enabled,
        "department_id": user.department_id,
        "department_name": user.department.name,
        "role_kind": user.role_kind,
        "remark": user.remark,
        "tenant": user.tenant,
        "created_at": iso8601_z(user.created_at),
        "tags": _named(sorted(user.tags, key=lambda tag: tag.id)),
        "user_roles": _named(sorted(user.roles, key=lambda role: role.id)),
        "department_roles": _named(roles),
        "data_scope": _named(sorted(user.data_scope_departments, key=lambda dept: dept.id)),
    }


async def department_subtree_ids(session: AsyncSession, root_id: str) -> list[str]:
    if await session.get(Department, root_id) is None:
        return []
    tree = select(Department.id).where(Department.id == root_id).cte(name="dept_tree", recursive=True)
    child = aliased(Department)
    tree = tree.union_all(select(child.id).where(child.parent_id == tree.c.id))
    result = await session.execute(select(tree.c.id))
    return list(result.scalars().all())


@router.get("/users", response_model=Envelope[PageData[UserListItem]])
async def list_users(
    session: SessionDep,
    _principal: PrincipalDep,
    params: Annotated[PageParams, Depends(page_params)],
    department_id: str | None = None,
    include_descendants: bool = Query(True),
    nickname: str | None = None,
    login_account: str | None = None,
    enabled: bool | None = None,
) -> dict:
    filters = []
    if department_id:
        dept_ids = (
            await department_subtree_ids(session, department_id)
            if include_descendants
            else [department_id]
        )
        if not dept_ids:
            return success(page_data([], 0, params))
        filters.append(User.department_id.in_(dept_ids))
    if nickname:
        filters.append(User.nickname.ilike(f"%{nickname.strip()}%"))
    if login_account:
        filters.append(User.login_account.ilike(f"%{login_account.strip()}%"))
    if enabled is not None:
        filters.append(User.enabled.is_(enabled))

    total = int(
        (await session.execute(select(func.count()).select_from(User).where(*filters))).scalar_one()
    )
    result = await session.execute(
        select(User)
        .options(*_USER_LOAD)
        .where(*filters)
        .order_by(User.created_at.desc(), User.id)
        .offset(params.offset)
        .limit(params.page_size)
    )
    users = list(result.scalars().unique().all())
    role_map = await department_roles_by_dept(session, [user.department_id for user in users])
    items = [serialize_user(user, role_map.get(user.department_id, [])) for user in users]
    return success(page_data(items, total, params))


@router.post("/users", response_model=Envelope[UserListItem])
async def create_user(
    body: CreateUserRequest,
    session: SessionDep,
    principal: PrincipalDep,
) -> dict:
    await get_department(session, body.department_id)
    existing = await session.execute(
        select(User.id).where(User.login_account == body.login_account)
    )
    if existing.scalar_one_or_none() is not None:
        raise ApiError(409, "CONFLICT", "login_account 已存在")

    user = User(
        nickname=body.nickname,
        login_account=body.login_account,
        short_name=body.short_name,
        password_hash=await hash_password_or_default(session, body.password),
        phone=body.phone,
        enabled=True,
        department_id=body.department_id,
        role_kind="成员",
        remark=body.remark,
        tenant=body.tenant or principal["tenant"],
    )
    session.add(user)
    try:
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise ApiError(409, "CONFLICT", "login_account 已存在") from exc
    user = await get_user(session, user.id)
    roles = (await department_roles_by_dept(session, [user.department_id])).get(
        user.department_id, []
    )
    return success(serialize_user(user, roles))


@router.put("/users/{user_id}", response_model=Envelope[UserListItem])
async def update_user(
    user_id: str,
    body: UpdateUserRequest,
    session: SessionDep,
    _principal: PrincipalDep,
) -> dict:
    user = await get_user(session, user_id)
    await get_department(session, body.department_id)
    user.nickname = body.nickname
    user.short_name = body.short_name
    user.phone = body.phone
    user.department_id = body.department_id
    user.role_kind = body.role_kind
    user.remark = body.remark
    await session.commit()
    user = await get_user(session, user_id)
    roles = (await department_roles_by_dept(session, [user.department_id])).get(
        user.department_id, []
    )
    return success(serialize_user(user, roles))


@router.patch("/users/{user_id}/status", response_model=Envelope[IdEnabled])
async def set_user_status(
    user_id: str,
    body: SetUserStatusRequest,
    session: SessionDep,
    _principal: PrincipalDep,
) -> dict:
    user = await get_user(session, user_id)
    user.enabled = body.enabled
    await session.commit()
    return success({"id": user.id, "enabled": user.enabled})
