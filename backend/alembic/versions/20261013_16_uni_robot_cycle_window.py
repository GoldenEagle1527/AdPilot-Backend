"""全域机器人补上周期分钟和每天结束时间。

Revision ID: 20261013_16
Revises: 20261013_15
Create Date: 2026-10-13

推广链可以选周期，并记下每天的结束时分。已有行这三列为空。
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20261013_16"
down_revision: Union[str, None] = "20261013_15"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "uni_robot_rule",
        sa.Column("cycle_minutes", sa.Integer(), nullable=True, comment="周期分钟。推广链选周期时用"),
    )
    op.add_column(
        "uni_robot_rule",
        sa.Column("schedule_end_hour", sa.Integer(), nullable=True, comment="每天结束小时"),
    )
    op.add_column(
        "uni_robot_rule",
        sa.Column("schedule_end_minute", sa.Integer(), nullable=True, comment="每天结束分钟"),
    )
    op.create_check_constraint(
        "ck_uni_robot_rule_schedule_kind",
        "uni_robot_rule",
        "schedule_kind IN ('daily', 'cycle')",
    )
    op.create_check_constraint("ck_uni_robot_rule_sort", "uni_robot_rule", "sort_order >= 0")
    op.create_check_constraint(
        "ck_uni_robot_rule_cycle",
        "uni_robot_rule",
        "cycle_minutes IS NULL OR cycle_minutes BETWEEN 1 AND 1440",
    )
    op.create_check_constraint(
        "ck_uni_robot_rule_end_hour",
        "uni_robot_rule",
        "schedule_end_hour IS NULL OR schedule_end_hour BETWEEN 0 AND 23",
    )
    op.create_check_constraint(
        "ck_uni_robot_rule_end_minute",
        "uni_robot_rule",
        "schedule_end_minute IS NULL OR schedule_end_minute BETWEEN 0 AND 59",
    )


def downgrade() -> None:
    op.drop_constraint("ck_uni_robot_rule_end_minute", "uni_robot_rule", type_="check")
    op.drop_constraint("ck_uni_robot_rule_end_hour", "uni_robot_rule", type_="check")
    op.drop_constraint("ck_uni_robot_rule_cycle", "uni_robot_rule", type_="check")
    op.drop_constraint("ck_uni_robot_rule_sort", "uni_robot_rule", type_="check")
    op.drop_constraint("ck_uni_robot_rule_schedule_kind", "uni_robot_rule", type_="check")
    op.drop_column("uni_robot_rule", "schedule_end_minute")
    op.drop_column("uni_robot_rule", "schedule_end_hour")
    op.drop_column("uni_robot_rule", "cycle_minutes")
