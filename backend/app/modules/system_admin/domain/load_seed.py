"""把 system_admin 种子写入当前环境的数据库。"""

from __future__ import annotations

import asyncio

from sqlalchemy import func, select, text

from app.core.db import dispose_engine, get_session
from app.modules.system_admin.domain.models import (
    Department,
    DepartmentTag,
    DictItem,
    MenuNode,
    Role,
    RoleMenu,
    User,
    UserDataScope,
    UserRole,
    UserTag,
)
from app.modules.system_admin.domain.seed_data import (
    LOCAL_DEPARTMENTS,
    dict_seed_rows,
    local_data_scope_seed_rows,
    local_user_role_seed_rows,
    local_user_seed_rows,
    menu_seed_rows,
    role_menu_seed_rows,
    role_seed_rows,
)
from app.modules.system_admin.domain.tags import DEPARTMENT_TAG_SEED, USER_TAG_SEED

_EXPLICIT_ID_TABLES = (
    "department_tags",
    "user_tags",
    "departments",
    "roles",
    "menu_nodes",
    "dict_items",
    "users",
)


async def _sync_identity(session, table: str) -> None:
    """把自增序列拨到该表当前最大 id，避免下次插入撞主键。"""
    if table not in _EXPLICIT_ID_TABLES:
        raise RuntimeError(f"拒绝同步未列入白名单的表：{table}")
    await session.execute(
        text(
            f"SELECT setval(pg_get_serial_sequence('{table}', 'id'), "
            f"COALESCE((SELECT MAX(id) FROM {table}), 1), true)"
        )
    )


async def load_seed() -> None:
    """写入部门、标签、角色、菜单、字典和本地账号。已有用户则整批跳过。"""
    async for session in get_session():
        existing = await session.scalar(select(func.count()).select_from(User))
        if existing:
            print(f"已有 {existing} 个用户，跳过灌种")
            return
        for row in DEPARTMENT_TAG_SEED:
            session.add(DepartmentTag(**row))
        for row in USER_TAG_SEED:
            session.add(UserTag(**row))
        await session.flush()
        for row in LOCAL_DEPARTMENTS:
            session.add(Department(**row))
            await session.flush()
        for row in role_seed_rows():
            session.add(Role(**row))
        for row in dict_seed_rows():
            session.add(DictItem(**row))
        await session.flush()
        for row in menu_seed_rows():
            session.add(MenuNode(**row))
            await session.flush()
        for row in local_user_seed_rows():
            session.add(User(**row))
        await session.flush()
        for row in role_menu_seed_rows():
            session.add(RoleMenu(**row))
        for row in local_user_role_seed_rows():
            session.add(UserRole(**row))
        for row in local_data_scope_seed_rows():
            session.add(UserDataScope(**row))
        await session.flush()
        for table in _EXPLICIT_ID_TABLES:
            await _sync_identity(session, table)
        await session.commit()
        print(
            "种子已写入："
            f"部门 {len(LOCAL_DEPARTMENTS)}，"
            f"角色 {len(role_seed_rows())}，"
            f"菜单 {len(menu_seed_rows())}，"
            f"用户 {len(local_user_seed_rows())}"
        )


def main() -> None:
    """命令行入口：按 ADPILOT_ENV 连接并灌种。"""

    async def _run() -> None:
        try:
            await load_seed()
        finally:
            await dispose_engine()

    asyncio.run(_run())


if __name__ == "__main__":
    main()
