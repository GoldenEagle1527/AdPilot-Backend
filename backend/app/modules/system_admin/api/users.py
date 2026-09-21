"""用户主档：分页查询、新增、改主档、启停、软删。"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.auth import drop_user_sessions
from app.core.envelope import ApiError, Envelope, success
from app.core.pagination import PageData, PageParams, page_data, page_params
from app.core.times import beijing_iso
from app.modules.system_admin.deps import MENU_USERS, SessionDep, require_menu
from app.modules.system_admin.domain.access import (
    assert_user_manager_remains,
    publish_acl_for_users,
)
from app.modules.system_admin.domain.enums import ROLE_KIND_MEMBER
from app.modules.system_admin.domain.ids import parse_int_id, require_int_id
from app.modules.system_admin.domain.models import Department, DepartmentRole, Role, User
from app.modules.system_admin.domain.org import department_subtree_ids, user_not_deleted
from app.modules.system_admin.domain.password import hash_password_or_default
from app.modules.system_admin.schemas.common import DeletedId, IdEnabled, UserListItem
from app.modules.system_admin.schemas.users import (
    CreateUserRequest,
    SetUserStatusRequest,
    UpdateUserRequest,
)

router = APIRouter(prefix="/api/v1/system-admin", tags=["system-admin"])

PrincipalDep = Annotated[dict[str, str], Depends(require_menu(MENU_USERS))]
_USER_LOAD = (
    selectinload(User.tags),
    selectinload(User.roles),
    selectinload(User.data_scope_departments),
    selectinload(User.department),
)


async def get_department(
    session: AsyncSession, department_id: str, *, require_enabled: bool = False
) -> Department:
    department_id = require_int_id(department_id, "部门不存在")
    department = await session.get(Department, int(department_id))
    if department is None or department.is_deleted:
        raise ApiError(404, "NOT_FOUND", "部门不存在")
    if require_enabled and not department.enabled:
        raise ApiError(409, "DEPARTMENT_DISABLED", "部门已停用")
    return department


async def get_user(session: AsyncSession, user_id: str) -> User:
    user_id = require_int_id(user_id, "用户不存在")
    result = await session.execute(
        select(User).options(*_USER_LOAD).where(User.id == int(user_id), user_not_deleted())
    )
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
    return [{"id": str(item.id), "name": item.name} for item in items]


def serialize_user(user: User, department_roles: list[Role] | None = None) -> dict:
    roles = department_roles if department_roles is not None else []
    return {
        "id": str(user.id),
        "nickname": user.nickname,
        "login_account": user.login_account,
        "short_name": user.short_name,
        "phone": user.phone,
        "enabled": user.enabled,
        "department_id": str(user.department_id),
        "department_name": user.department.name,
        "role_kind": user.role_kind,
        "remark": user.remark,
        "tenant": user.tenant,
        "created_at": beijing_iso(user.created_date),
        "tags": _named(sorted(user.tags, key=lambda tag: tag.id)),
        "user_roles": _named(sorted(user.roles, key=lambda role: role.id)),
        "department_roles": _named(roles),
        "data_scope": _named(
            sorted(
                [dept for dept in user.data_scope_departments if not dept.is_deleted],
                key=lambda dept: dept.id,
            )
        ),
    }


@router.get(
    "/users",
    response_model=Envelope[PageData[UserListItem]],
    summary="分页查询用户",
)
async def list_users(
    session: SessionDep,
    _principal: PrincipalDep,
    params: Annotated[PageParams, Depends(page_params)],
    department_id: str | None = None,
    include_descendants: bool = Query(True),
    nickname: str | None = None,
    login_account: str | None = None,
    enabled: bool | None = None,
    id: str | None = None,
    phone: str | None = None,
) -> dict:
    """按部门（可含子孙）、昵称、账号、手机、启用状态分页列出未删除用户。"""
    filters = [user_not_deleted()]
    if id:
        parsed = parse_int_id(id.strip())
        if parsed is None:
            return success(page_data([], 0, params))
        filters.append(User.id == int(parsed))
    if department_id:
        parsed_dept = parse_int_id(department_id)
        if parsed_dept is None:
            return success(page_data([], 0, params))
        dept_ids = (
            await department_subtree_ids(session, parsed_dept)
            if include_descendants
            else [parsed_dept]
        )
        if not dept_ids:
            return success(page_data([], 0, params))
        filters.append(User.department_id.in_([int(item) for item in dept_ids]))
    if nickname:
        filters.append(User.nickname.ilike(f"%{nickname.strip()}%"))
    if login_account:
        filters.append(User.login_account == login_account.strip())
    if phone:
        filters.append(User.phone == phone.strip())
    if enabled is not None:
        filters.append(User.enabled.is_(enabled))

    total = int(
        (await session.execute(select(func.count()).select_from(User).where(*filters))).scalar_one()
    )
    result = await session.execute(
        select(User)
        .options(*_USER_LOAD)
        .where(*filters)
        .order_by(User.created_date.desc(), User.id)
        .offset(params.offset)
        .limit(params.page_size)
    )
    users = list(result.scalars().unique().all())
    role_map = await department_roles_by_dept(session, [user.department_id for user in users])
    items = [serialize_user(user, role_map.get(user.department_id, [])) for user in users]
    return success(page_data(items, total, params))


@router.post("/users", response_model=Envelope[UserListItem], summary="新增用户")
async def create_user(
    body: CreateUserRequest,
    session: SessionDep,
    principal: PrincipalDep,
) -> dict:
    """在指定部门下创建用户；登录账号唯一，默认启用、职务为成员。"""
    department = await get_department(session, body.department_id, require_enabled=True)
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
        department_id=department.id,
        role_kind=ROLE_KIND_MEMBER,
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


@router.put("/users/{user_id}", response_model=Envelope[UserListItem], summary="改用户主档")
async def update_user(
    user_id: str,
    body: UpdateUserRequest,
    session: SessionDep,
    _principal: PrincipalDep,
) -> dict:
    """改昵称、部门、职务等；不改登录账号。"""
    user = await get_user(session, user_id)
    department = await get_department(session, body.department_id, require_enabled=True)
    user.nickname = body.nickname
    user.short_name = body.short_name
    user.phone = body.phone
    user.department_id = department.id
    user.role_kind = body.role_kind
    user.remark = body.remark
    await session.commit()
    await publish_acl_for_users(session, [str(user.id)])
    user = await get_user(session, user_id)
    roles = (await department_roles_by_dept(session, [user.department_id])).get(
        user.department_id, []
    )
    return success(serialize_user(user, roles))


@router.patch("/users/{user_id}/status", response_model=Envelope[IdEnabled], summary="用户启停")
async def set_user_status(
    user_id: str,
    body: SetUserStatusRequest,
    session: SessionDep,
    principal: PrincipalDep,
) -> dict:
    """启用或停用用户；停用会踢掉其登录会话。"""
    user = await get_user(session, user_id)
    if not body.enabled and principal["id"] == str(user.id):
        raise ApiError(409, "CANNOT_DISABLE_SELF", "不能停用当前登录账号")
    user.enabled = body.enabled
    if not body.enabled:
        await assert_user_manager_remains(session)
    await session.commit()
    if not body.enabled:
        await drop_user_sessions(str(user.id))
    else:
        await publish_acl_for_users(session, [str(user.id)])
    return success({"id": str(user.id), "enabled": user.enabled})


@router.delete("/users/{user_id}", response_model=Envelope[DeletedId], summary="软删用户")
async def delete_user(
    user_id: str,
    session: SessionDep,
    principal: PrincipalDep,
) -> dict:
    """软删用户并踢掉其登录会话；不能删当前登录账号。"""
    user = await get_user(session, user_id)
    if principal["id"] == str(user.id):
        raise ApiError(409, "CANNOT_DELETE_SELF", "不能删除当前登录账号")
    user.mark_deleted()
    await assert_user_manager_remains(session)
    await session.commit()
    await drop_user_sessions(str(user.id))
    return success({"id": str(user.id), "deleted": True})
