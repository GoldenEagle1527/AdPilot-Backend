"""漫剧表补上模型已映射、库里还没有的列。

Revision ID: 20261008_02
Revises: 20261008_01
Create Date: 2026-10-08

只加列，不改已有列，不删列。非空列带默认值，已有行可以加上。
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20261008_02"
down_revision: Union[str, None] = "20261008_01"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "manhua_series",
        sa.Column(
            "tab_text",
            sa.String(length=128),
            nullable=False,
            server_default=sa.text("''"),
            comment="由 single_price 判断：不收费 IAA，收费 IAP",
        ),
    )
    op.add_column(
        "manhua_series",
        sa.Column(
            "promotion_triggered",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
            comment="到预估可投时间后是否已自动建过推广链同步任务",
        ),
    )


def downgrade() -> None:
    op.drop_column("manhua_series", "promotion_triggered")
    op.drop_column("manhua_series", "tab_text")
