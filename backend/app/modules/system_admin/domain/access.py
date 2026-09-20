from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.modules.system_admin.domain.models import (
    DepartmentRole,
    MenuNode,
    Role,
    RoleMenu,
    User,
    UserRole,
)
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
        .where(User.login_account == login_account)
    )
    return result.scalar_one_or_none()


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
            if node.type == "目录" and not kids:
                continue
            items.append(_to_menu_node(node, kids))
        return items

    return walk(None)
