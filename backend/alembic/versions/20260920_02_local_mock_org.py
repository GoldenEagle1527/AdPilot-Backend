"""本地 mock 部门 / 用户，对齐 core 登录账号。

Revision ID: 20260920_02
Revises: 20260920_01
Create Date: 2026-09-20

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

from app.modules.system_admin.domain.models import Base
from app.modules.system_admin.domain.seed_data import (
    LOCAL_DEPARTMENTS,
    local_data_scope_seed_rows,
    local_user_role_seed_rows,
    local_user_seed_rows,
)

revision: str = "20260920_02"
down_revision: Union[str, None] = "20260920_01"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    tables = Base.metadata.tables
    op.bulk_insert(tables["departments"], LOCAL_DEPARTMENTS)
    op.bulk_insert(tables["users"], local_user_seed_rows())
    op.bulk_insert(tables["user_roles"], local_user_role_seed_rows())
    op.bulk_insert(tables["user_data_scopes"], local_data_scope_seed_rows())
    for table in ("departments", "users"):
        op.execute(
            sa.text(
                f"SELECT setval(pg_get_serial_sequence('{table}', 'id'), "
                f"COALESCE((SELECT MAX(id) FROM {table}), 1), "
                f"(SELECT EXISTS (SELECT 1 FROM {table})))"
            )
        )


def downgrade() -> None:
    op.execute("DELETE FROM user_data_scopes WHERE user_id IN ('1', '3')")
    op.execute("DELETE FROM user_roles WHERE user_id IN ('1', '3')")
    op.execute("DELETE FROM users WHERE id IN ('1', '2', '3')")
    op.execute("DELETE FROM departments WHERE id IN ('1', '2')")
