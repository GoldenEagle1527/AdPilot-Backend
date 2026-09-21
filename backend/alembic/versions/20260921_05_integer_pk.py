"""integer identity primary keys.

Revision ID: 20260921_05
Revises: 20260920_04
Create Date: 2026-09-21

已落地库若仍是 varchar 雪花主键：重建系统管理表并重种本地种子；漫剧缓存表丢掉后由同步任务回填。
新库 01–04 已是整数 Identity 时本迁移为空操作。
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

from app.core.db import Base
from app.modules.material.domain.models import ManhuaSeries  # noqa: F401
from app.modules.system_admin.domain.models import Base as AdminBase
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

revision: str = "20260921_05"
down_revision: Union[str, None] = "20260920_04"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _id_is_integer(table: str) -> bool:
    bind = op.get_bind()
    inspector = inspect(bind)
    if table not in inspector.get_table_names():
        return False
    col = next(c for c in inspector.get_columns(table) if c["name"] == "id")
    return "int" in type(col["type"]).__name__.lower()


def _reset_identity(table: str) -> None:
    op.execute(
        sa.text(
            f"SELECT setval(pg_get_serial_sequence('{table}', 'id'), "
            f"COALESCE((SELECT MAX(id) FROM {table}), 1), "
            f"(SELECT EXISTS (SELECT 1 FROM {table})))"
        )
    )


def _reseed_admin() -> None:
    tables = AdminBase.metadata.tables
    op.bulk_insert(tables["roles"], role_seed_rows())
    op.bulk_insert(tables["menu_nodes"], menu_seed_rows())
    op.bulk_insert(tables["role_menus"], role_menu_seed_rows())
    op.bulk_insert(tables["dict_items"], dict_seed_rows())
    op.bulk_insert(tables["departments"], LOCAL_DEPARTMENTS)
    op.bulk_insert(tables["users"], local_user_seed_rows())
    op.bulk_insert(tables["user_roles"], local_user_role_seed_rows())
    op.bulk_insert(tables["user_data_scopes"], local_data_scope_seed_rows())
    op.bulk_insert(tables["department_tags"], DEPARTMENT_TAG_SEED)
    op.bulk_insert(tables["user_tags"], USER_TAG_SEED)
    for table in (
        "roles",
        "menu_nodes",
        "dict_items",
        "departments",
        "users",
        "department_tags",
        "user_tags",
    ):
        _reset_identity(table)


def upgrade() -> None:
    bind = op.get_bind()
    if not _id_is_integer("departments"):
        Base.metadata.drop_all(bind)
        Base.metadata.create_all(bind)
        _reseed_admin()
        return
    if not _id_is_integer("manhua_series"):
        op.drop_table("manhua_series")
        ManhuaSeries.__table__.create(bind)


def downgrade() -> None:
    pass
