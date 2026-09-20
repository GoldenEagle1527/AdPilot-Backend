"""soft-delete, role.updated_by, closed tag catalogs.

Revision ID: 20260920_03
Revises: 20260920_02
Create Date: 2026-09-20

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

from app.modules.system_admin.domain.models import Base
from app.modules.system_admin.domain.tags import DEPARTMENT_TAG_SEED, USER_TAG_SEED

revision: str = "20260920_03"
down_revision: Union[str, None] = "20260920_02"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _column_names(table: str) -> set[str]:
    return {col["name"] for col in inspect(op.get_bind()).get_columns(table)}


def upgrade() -> None:
    if "deleted_at" not in _column_names("departments"):
        op.add_column("departments", sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True))
    if "deleted_at" not in _column_names("users"):
        op.add_column("users", sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True))
    if "updated_by" not in _column_names("roles"):
        op.add_column("roles", sa.Column("updated_by", sa.String(length=64), nullable=True))

    bind = op.get_bind()
    tables = Base.metadata.tables
    dept_n = bind.execute(sa.text("SELECT count(*) FROM department_tags")).scalar()
    if not dept_n:
        op.bulk_insert(tables["department_tags"], DEPARTMENT_TAG_SEED)
    user_n = bind.execute(sa.text("SELECT count(*) FROM user_tags")).scalar()
    if not user_n:
        op.bulk_insert(tables["user_tags"], USER_TAG_SEED)


def downgrade() -> None:
    op.execute("DELETE FROM department_tag_links")
    op.execute("DELETE FROM user_tag_links")
    op.execute("DELETE FROM department_tags WHERE id IN ('1', '2', '3', '4')")
    op.execute("DELETE FROM user_tags WHERE id IN ('1', '2')")
    cols_roles = _column_names("roles")
    cols_users = _column_names("users")
    cols_depts = _column_names("departments")
    if "updated_by" in cols_roles:
        op.drop_column("roles", "updated_by")
    if "deleted_at" in cols_users:
        op.drop_column("users", "deleted_at")
    if "deleted_at" in cols_depts:
        op.drop_column("departments", "deleted_at")
