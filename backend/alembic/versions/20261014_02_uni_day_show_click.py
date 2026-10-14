"""全域日表补展示、点击，并建首页自选字段表。

Revision ID: 20261014_02
Revises: 20261014_01
Create Date: 2026-10-14
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

from app.modules.report.refresh import backfill_uni_show_click

revision: str = "20261014_02"
down_revision: Union[str, None] = "20261014_01"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_UNI_TABLES = (
    "report_uni_drama_day",
    "report_uni_pitcher_drama_day",
    "report_uni_pitcher_day",
    "report_uni_group_day",
)


def _common() -> list[sa.Column]:
    return [
        sa.Column("id", sa.Integer(), sa.Identity(), primary_key=True),
        sa.Column("is_deleted", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_date", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_date", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    ]


def upgrade() -> None:
    for table in _UNI_TABLES:
        op.add_column(
            table,
            sa.Column("all_show_cnt_trend", sa.BigInteger(), nullable=False, server_default="0"),
        )
        op.add_column(
            table,
            sa.Column("all_click_cnt_trend", sa.BigInteger(), nullable=False, server_default="0"),
        )
    op.create_table(
        "report_home_field",
        *_common(),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("surface", sa.String(32), nullable=False),
        sa.Column("field_1", sa.String(64), nullable=False),
        sa.Column("field_2", sa.String(64), nullable=False),
        sa.Column("field_3", sa.String(64), nullable=False),
        sa.UniqueConstraint("user_id", "surface", name="uq_report_home_field_user_surface"),
        sa.CheckConstraint(
            "surface IN ('manhua', 'uni_drama', 'uni_pitcher_drama', 'uni_pitcher', 'uni_group')",
            name="ck_report_home_field_surface",
        ),
    )
    backfill_uni_show_click(op.get_bind())


def downgrade() -> None:
    op.drop_table("report_home_field")
    for table in _UNI_TABLES:
        op.drop_column(table, "all_click_cnt_trend")
        op.drop_column(table, "all_show_cnt_trend")
