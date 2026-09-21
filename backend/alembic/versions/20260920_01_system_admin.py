"""system-admin ORM tables and reference seeds.

Revision ID: 20260920_01
Revises:
Create Date: 2026-09-20

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

from app.modules.system_admin.domain.models import Base
from app.modules.system_admin.domain.seed_data import (
    dict_seed_rows,
    menu_seed_rows,
    role_menu_seed_rows,
    role_seed_rows,
)

revision: str = "20260920_01"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    Base.metadata.create_all(bind)
    tables = Base.metadata.tables
    op.bulk_insert(tables["roles"], role_seed_rows())
    op.bulk_insert(tables["menu_nodes"], menu_seed_rows())
    op.bulk_insert(tables["role_menus"], role_menu_seed_rows())
    op.bulk_insert(tables["dict_items"], dict_seed_rows())
    for table in ("roles", "menu_nodes", "dict_items"):
        op.execute(
            sa.text(
                f"SELECT setval(pg_get_serial_sequence('{table}', 'id'), "
                f"COALESCE((SELECT MAX(id) FROM {table}), 1), "
                f"(SELECT EXISTS (SELECT 1 FROM {table})))"
            )
        )


def downgrade() -> None:
    bind = op.get_bind()
    Base.metadata.drop_all(bind)
