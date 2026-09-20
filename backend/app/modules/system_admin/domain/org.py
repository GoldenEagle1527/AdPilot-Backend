from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from app.modules.system_admin.domain.models import Department, User, UserDataScope


def user_not_deleted():
    return User.deleted_at.is_(None)


def department_not_deleted():
    return Department.deleted_at.is_(None)


async def department_subtree_ids(session: AsyncSession, root_id: str) -> list[str]:
    root = await session.get(Department, root_id)
    if root is None or root.deleted_at is not None:
        return []
    tree = (
        select(Department.id)
        .where(Department.id == root_id, department_not_deleted())
        .cte(name="dept_tree", recursive=True)
    )
    child = aliased(Department)
    tree = tree.union_all(
        select(child.id).where(child.parent_id == tree.c.id, child.deleted_at.is_(None))
    )
    result = await session.execute(select(tree.c.id))
    return list(result.scalars().all())


async def expand_department_ids(session: AsyncSession, department_ids: list[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for dept_id in department_ids:
        if dept_id in seen:
            continue
        for item in await department_subtree_ids(session, dept_id):
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
    return list(rows.scalars().all())


async def effective_data_scope(
    session: AsyncSession, user: User
) -> tuple[bool, list[str]]:
    stored = await stored_data_scope_ids(session, user)
    if not stored:
        return True, []
    return False, await expand_department_ids(session, stored)
