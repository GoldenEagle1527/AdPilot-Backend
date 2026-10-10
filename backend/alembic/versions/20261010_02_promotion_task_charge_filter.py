"""番茄推广链手动采集记下付费类型。

Revision ID: 20261010_02
Revises: 20261010_01
Create Date: 2026-10-10

自动任务这一列为空，执行时仍按短剧页签过滤。
手动批量采集写入 all、IAA 或 IAP。
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20261010_02"
down_revision: Union[str, None] = "20261010_01"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "theater_promotion_tasks",
        sa.Column(
            "charge_filter",
            sa.String(length=8),
            nullable=True,
            comment="手动批量采集的付费类型：all 全部、IAA 免费、IAP 付费。空表示自动任务，按短剧页签过滤",
        ),
    )
    op.create_check_constraint(
        "ck_theater_promotion_tasks_charge",
        "theater_promotion_tasks",
        "charge_filter IS NULL OR charge_filter IN ('all', 'IAA', 'IAP')",
    )


def downgrade() -> None:
    op.drop_constraint("ck_theater_promotion_tasks_charge", "theater_promotion_tasks", type_="check")
    op.drop_column("theater_promotion_tasks", "charge_filter")
