"""自动规则预约不再要求结束晚于开始。

Revision ID: 20261009_04
Revises: 20261009_03
Create Date: 2026-10-09

预约执行是一个时间点，只存 schedule_start。schedule_end 仍可空。
去掉成对且结束更晚的检查，已有列不动。
"""
from typing import Sequence, Union

from alembic import op

revision: str = "20261009_04"
down_revision: Union[str, None] = "20261009_03"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_OLD = (
    "(schedule_start IS NULL AND schedule_end IS NULL) OR "
    "(schedule_start IS NOT NULL AND schedule_end IS NOT NULL AND schedule_start < schedule_end)"
)


def upgrade() -> None:
    op.drop_constraint("ck_delivery_auto_rule_schedule", "delivery_auto_rule", type_="check")


def downgrade() -> None:
    op.create_check_constraint("ck_delivery_auto_rule_schedule", "delivery_auto_rule", _OLD)
