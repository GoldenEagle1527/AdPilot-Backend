from __future__ import annotations

from collections.abc import Iterable

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.envelope import ApiError
from app.modules.system_admin.domain.enums import MENU_TYPE_DIRECTORY
from app.modules.system_admin.domain.ids import parse_int_id
from app.modules.system_admin.domain.models import (
    Department,
    DepartmentRole,
    MenuNode,
    Role,
    RoleMenu,
    User,
    UserRole,
)
from app.modules.system_admin.domain.org import department_not_deleted, user_not_deleted
from app.modules.system_admin.domain.password import verify_password_async
from app.modules.system_admin.schemas.session import SessionMenuNode

# 系统管理页对应菜单树节点 id（权限清单 98–102）。
MENU_DEPARTMENTS = "98"
MENU_ROLES = "100"
MENU_USERS = "101"
MENU_ROLE_QUERY = "102"


async def user_by_login(session: AsyncSession, login_account: str) -> User | None:
    result = await session.execute(
        select(User)
        .options(selectinload(User.department))
        .where(User.login_account == login_account, user_not_deleted())
    )
    return result.scalar_one_or_none()


async def session_principal(session: AsyncSession, user: User) -> dict:
    """给 core 存进 Redis 的主体：身份 + 有效菜单。core 不解释菜单含义。"""
    menus = await effective_menu_ids(session, user)
    return {
        "id": str(user.id),
        "nickname": user.nickname,
        "login_account": user.login_account,
        "tenant": user.tenant,
        "enabled": user.enabled,
        "menu_ids": sorted(str(item) for item in menus),
    }


async def authenticate_password(
    session: AsyncSession, login: str, password: str
) -> tuple[str, dict | None]:
    """查库验密。返回 ('ok', principal) / ('disabled', None) / ('invalid', None)。不把 ORM 交给 core。"""
    user = await user_by_login(session, login)
    if user is None or not await verify_password_async(password, user.password_hash):
        return "invalid", None
    if not user.enabled:
        return "disabled", None
    return "ok", await session_principal(session, user)


async def user_ids_holding_role(session: AsyncSession, role_id: str) -> list[str]:
    parsed = parse_int_id(role_id)
    if parsed is None:
        return []
    role_pk = int(parsed)
    user_rows = await session.execute(
        select(UserRole.user_id)
        .join(User, User.id == UserRole.user_id)
        .where(UserRole.role_id == role_pk, user_not_deleted())
    )
    dept_rows = await session.execute(
        select(User.id)
        .join(DepartmentRole, DepartmentRole.department_id == User.department_id)
        .where(DepartmentRole.role_id == role_pk, user_not_deleted())
    )
    return list({str(row[0]) for row in user_rows.all()} | {str(row[0]) for row in dept_rows.all()})


async def user_ids_in_department(session: AsyncSession, department_id: str) -> list[str]:
    parsed = parse_int_id(department_id)
    if parsed is None:
        return []
    rows = await session.execute(
        select(User.id).where(User.department_id == int(parsed), user_not_deleted())
    )
    return [str(row[0]) for row in rows.all()]


async def publish_acl_for_users(session: AsyncSession, user_ids: Iterable[str]) -> None:
    from app.core.auth import drop_user_sessions, rewrite_user_sessions

    seen: set[str] = set()
    for user_id in user_ids:
        if user_id in seen:
            continue
        seen.add(user_id)
        parsed = parse_int_id(user_id)
        if parsed is None:
            continue
        user = await session.get(User, int(parsed))
        if user is None or user.is_deleted:
            await drop_user_sessions(parsed)
            continue
        await rewrite_user_sessions(parsed, await session_principal(session, user))


async def user_ids_holding_menu(session: AsyncSession, menu_id: str) -> set[str]:
    """启用且未删的用户，经用户角色或启用部门角色持有该菜单。"""
    parsed = parse_int_id(menu_id)
    if parsed is None:
        return set()
    menu_pk = int(parsed)
    via_user = (
        select(User.id)
        .join(UserRole, UserRole.user_id == User.id)
        .join(Role, Role.id == UserRole.role_id)
        .join(RoleMenu, RoleMenu.role_id == Role.id)
        .where(
            user_not_deleted(),
            User.enabled.is_(True),
            Role.enabled.is_(True),
            RoleMenu.menu_id == menu_pk,
        )
    )
    via_dept = (
        select(User.id)
        .join(Department, Department.id == User.department_id)
        .join(DepartmentRole, DepartmentRole.department_id == Department.id)
        .join(Role, Role.id == DepartmentRole.role_id)
        .join(RoleMenu, RoleMenu.role_id == Role.id)
        .where(
            user_not_deleted(),
            User.enabled.is_(True),
            department_not_deleted(),
            Department.enabled.is_(True),
            Role.enabled.is_(True),
            RoleMenu.menu_id == menu_pk,
        )
    )
    rows = await session.execute(via_user.union(via_dept))
    return {str(row[0]) for row in rows.all()}


async def assert_user_manager_remains(session: AsyncSession) -> None:
    await session.flush()
    if not await user_ids_holding_menu(session, MENU_USERS):
        raise ApiError(409, "至少保留一名可管理用户的账号")


async def assert_self_keeps_user_menu(session: AsyncSession, user_id: str) -> None:
    await session.flush()
    holders = await user_ids_holding_menu(session, MENU_USERS)
    if str(user_id) not in holders:
        raise ApiError(409, "不能去掉自己的用户管理权限")


async def effective_menu_ids(session: AsyncSession, user: User) -> set[str]:
    """用户角色 ∪ 部门角色，去掉停用角色。"""
    user_roles = await session.execute(
        select(UserRole.role_id)
        .join(Role, Role.id == UserRole.role_id)
        .where(UserRole.user_id == user.id, Role.enabled.is_(True))
    )
    dept_roles = await session.execute(
        select(DepartmentRole.role_id)
        .join(Role, Role.id == DepartmentRole.role_id)
        .join(Department, Department.id == DepartmentRole.department_id)
        .where(
            DepartmentRole.department_id == user.department_id,
            Role.enabled.is_(True),
            Department.enabled.is_(True),
            department_not_deleted(),
        )
    )
    role_ids = {row[0] for row in user_roles.all()} | {row[0] for row in dept_roles.all()}
    if not role_ids:
        return set()
    menus = await session.execute(select(RoleMenu.menu_id).where(RoleMenu.role_id.in_(role_ids)))
    return {str(row[0]) for row in menus.all()}


def _node_sort_key(node: MenuNode) -> tuple[int, str]:
    try:
        return (int(node.id), node.id)
    except ValueError:
        return (0, node.id)


def _to_menu_node(node: MenuNode, children: list[SessionMenuNode]) -> SessionMenuNode:
    return SessionMenuNode(
        id=str(node.id),
        name=node.name,
        type=node.type,
        parent_id=None if node.parent_id is None else str(node.parent_id),
        business_domain=node.business_domain,
        tenant_kind=node.tenant_kind,
        children=children,
    )


def build_menu_tree(nodes_by_id: dict[str, MenuNode], granted_ids: set[str]) -> list[SessionMenuNode]:
    if not granted_ids:
        return []

    keyed = {str(key): node for key, node in nodes_by_id.items()}
    keep: set[str] = {str(item) for item in granted_ids}
    for menu_id in list(keep):
        current = keyed.get(menu_id)
        while current is not None and current.parent_id:
            parent = keyed.get(str(current.parent_id))
            if parent is None:
                break
            keep.add(str(parent.id))
            current = parent

    children_of: dict[str | None, list[MenuNode]] = {}
    for menu_id in keep:
        node = keyed.get(menu_id)
        if node is None:
            continue
        parent_key = str(node.parent_id) if node.parent_id is not None and str(node.parent_id) in keep else None
        children_of.setdefault(parent_key, []).append(node)

    def walk(parent_id: str | None) -> list[SessionMenuNode]:
        siblings = children_of.get(parent_id, [])
        siblings.sort(key=_node_sort_key)
        items: list[SessionMenuNode] = []
        for node in siblings:
            kids = walk(str(node.id))
            if node.type == MENU_TYPE_DIRECTORY and not kids:
                continue
            items.append(_to_menu_node(node, kids))
        return items

    return walk(None)
