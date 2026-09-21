from __future__ import annotations

from collections.abc import Iterable

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.modules.system_admin.domain.enums import MENU_TYPE_DIRECTORY
from app.modules.system_admin.domain.models import (
    DepartmentRole,
    MenuNode,
    Role,
    RoleMenu,
    User,
    UserRole,
)
from app.modules.system_admin.domain.org import user_not_deleted
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
        "id": user.id,
        "nickname": user.nickname,
        "login_account": user.login_account,
        "tenant": user.tenant,
        "enabled": user.enabled,
        "menu_ids": sorted(menus),
    }


async def authenticate_password(
    session: AsyncSession, login: str, password: str
) -> tuple[str, dict | None]:
    """查库验密。返回 ('ok', principal) / ('disabled', None) / ('invalid', None)。不把 ORM 交给 core。"""
    user = await user_by_login(session, login)
    if user is None and login:
        result = await session.execute(
            select(User).where(
                User.phone == login, User.phone.is_not(None), user_not_deleted()
            )
        )
        user = result.scalar_one_or_none()
    if user is None or not await verify_password_async(password, user.password_hash):
        return "invalid", None
    if not user.enabled:
        return "disabled", None
    return "ok", await session_principal(session, user)


async def user_ids_holding_role(session: AsyncSession, role_id: str) -> list[str]:
    user_rows = await session.execute(
        select(UserRole.user_id)
        .join(User, User.id == UserRole.user_id)
        .where(UserRole.role_id == role_id, user_not_deleted())
    )
    dept_rows = await session.execute(
        select(User.id)
        .join(DepartmentRole, DepartmentRole.department_id == User.department_id)
        .where(DepartmentRole.role_id == role_id, user_not_deleted())
    )
    return list({row[0] for row in user_rows.all()} | {row[0] for row in dept_rows.all()})


async def user_ids_in_department(session: AsyncSession, department_id: str) -> list[str]:
    rows = await session.execute(
        select(User.id).where(User.department_id == department_id, user_not_deleted())
    )
    return [row[0] for row in rows.all()]


async def publish_acl_for_users(session: AsyncSession, user_ids: Iterable[str]) -> None:
    from app.core.auth import drop_user_sessions, rewrite_user_sessions

    seen: set[str] = set()
    for user_id in user_ids:
        if user_id in seen:
            continue
        seen.add(user_id)
        user = await session.get(User, user_id)
        if user is None or user.deleted_at is not None:
            await drop_user_sessions(user_id)
            continue
        await rewrite_user_sessions(user_id, await session_principal(session, user))


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
        .where(DepartmentRole.department_id == user.department_id, Role.enabled.is_(True))
    )
    role_ids = {row[0] for row in user_roles.all()} | {row[0] for row in dept_roles.all()}
    if not role_ids:
        return set()
    menus = await session.execute(select(RoleMenu.menu_id).where(RoleMenu.role_id.in_(role_ids)))
    return {row[0] for row in menus.all()}


def _node_sort_key(node: MenuNode) -> tuple[int, str]:
    try:
        return (int(node.id), node.id)
    except ValueError:
        return (0, node.id)


def _to_menu_node(node: MenuNode, children: list[SessionMenuNode]) -> SessionMenuNode:
    return SessionMenuNode(
        id=node.id,
        name=node.name,
        type=node.type,
        parent_id=node.parent_id,
        business_domain=node.business_domain,
        tenant_kind=node.tenant_kind,
        children=children,
    )


def build_menu_tree(nodes_by_id: dict[str, MenuNode], granted_ids: set[str]) -> list[SessionMenuNode]:
    if not granted_ids:
        return []

    keep: set[str] = set(granted_ids)
    for menu_id in list(granted_ids):
        current = nodes_by_id.get(menu_id)
        while current is not None and current.parent_id:
            parent = nodes_by_id.get(current.parent_id)
            if parent is None:
                break
            keep.add(parent.id)
            current = parent

    children_of: dict[str | None, list[MenuNode]] = {}
    for menu_id in keep:
        node = nodes_by_id.get(menu_id)
        if node is None:
            continue
        parent_key = node.parent_id if node.parent_id in keep else None
        children_of.setdefault(parent_key, []).append(node)

    def walk(parent_id: str | None) -> list[SessionMenuNode]:
        siblings = children_of.get(parent_id, [])
        siblings.sort(key=_node_sort_key)
        items: list[SessionMenuNode] = []
        for node in siblings:
            kids = walk(node.id)
            if node.type == MENU_TYPE_DIRECTORY and not kids:
                continue
            items.append(_to_menu_node(node, kids))
        return items

    return walk(None)
