from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from app.modules.system_admin.domain.ids import parse_int_id
from app.modules.system_admin.domain.models import Department, User, UserDataScope


def user_not_deleted():
    return User.deleted_at.is_(None)


def department_not_deleted():
    return Department.deleted_at.is_(None)


async def department_subtree_ids(
    session: AsyncSession, root_id: str, *, enabled_only: bool = False
) -> list[str]:
    parsed = parse_int_id(root_id)
    if parsed is None:
        return []
    root = await session.get(Department, int(parsed))
    if root is None or root.deleted_at is not None:
        return []
    if enabled_only and not root.enabled:
        return []
    root_filters = [Department.id == int(parsed), department_not_deleted()]
    if enabled_only:
        root_filters.append(Department.enabled.is_(True))
    tree = select(Department.id).where(*root_filters).cte(name="dept_tree", recursive=True)
    child = aliased(Department)
    child_filters = [child.parent_id == tree.c.id, child.deleted_at.is_(None)]
    if enabled_only:
        child_filters.append(child.enabled.is_(True))
    tree = tree.union_all(select(child.id).where(*child_filters))
    result = await session.execute(select(tree.c.id))
    return [str(item) for item in result.scalars().all()]


async def expand_department_ids(
    session: AsyncSession, department_ids: list[str], *, enabled_only: bool = False
) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for dept_id in department_ids:
        if dept_id in seen:
            continue
        for item in await department_subtree_ids(session, dept_id, enabled_only=enabled_only):
            if item not in seen:
                seen.add(item)
                ordered.append(item)
    return ordered


async def stored_data_scope_ids(session: AsyncSession, user: User) -> list[str]:
    rows = await session.execute(
        select(UserDataScope.department_id)
        .join(Department, Department.id == UserDataScope.department_id)
        .where(UserDataScope.user_id == user.id, department_not_deleted())
        .order_by(UserDataScope.department_id)
    )
    return [str(item) for item in rows.scalars().all()]


async def effective_data_scope(
    session: AsyncSession, user: User
) -> tuple[bool, list[str]]:
    stored = await stored_data_scope_ids(session, user)
    if not stored:
        return True, []
    expanded = await expand_department_ids(session, stored, enabled_only=True)
    if not expanded:
        return True, []
    return False, expanded
