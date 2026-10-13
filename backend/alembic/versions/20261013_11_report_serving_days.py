"""报表日表：列表直接读，小时任务从原始快照刷新。

Revision ID: 20261013_11
Revises: 20261013_10
Create Date: 2026-10-13
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20261013_11"
down_revision: Union[str, None] = "20261013_10"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _common() -> list[sa.Column]:
    return [
        sa.Column("id", sa.Integer(), sa.Identity(), primary_key=True),
        sa.Column("is_deleted", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_date", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_date", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    ]


def _money(name: str) -> sa.Column:
    return sa.Column(name, sa.Numeric(18, 2), nullable=False)


def _manhua_metrics() -> list[sa.Column]:
    return [
        _money("stat_cost"),
        _money("stat_pay_amount"),
        _money("attribution_game_in_app_ltv_1day"),
        _money("attribution_game_in_app_ltv_8days"),
        _money("attribution_micro_game_0d_ltv"),
        _money("attribution_micro_game_7d_ltv"),
        sa.Column("show_cnt", sa.BigInteger(), nullable=False),
        sa.Column("click_cnt", sa.BigInteger(), nullable=False),
        sa.Column("convert_cnt", sa.BigInteger(), nullable=False),
        sa.Column("active", sa.BigInteger(), nullable=False),
    ]


def _uni_metrics() -> list[sa.Column]:
    return [
        _money("all_stat_cost_trend"),
        _money("all_stat_total_cost_trend"),
        _money("all_gmv_trend"),
        _money("all_billing_gmv_0day_trend"),
        _money("all_billing_gmv_24h_trend"),
        _money("all_billing_gmv_3days_trend"),
        _money("all_income_trend"),
        _money("all_income_0day_trend"),
        _money("all_pay_amount_income_trend"),
        _money("all_micro_game_income_trend"),
        sa.Column("new_project_count", sa.Integer(), nullable=False, server_default="0"),
    ]


def upgrade() -> None:
    int_array = postgresql.ARRAY(sa.Integer())
    text_array = postgresql.ARRAY(sa.Text())
    big_array = postgresql.ARRAY(sa.BigInteger())
    op.create_table(
        "report_manhua_drama_day",
        *_common(),
        sa.Column("stat_date", sa.Date(), nullable=False),
        sa.Column("charge_mode", sa.String(8), nullable=False),
        sa.Column("series_id", sa.Integer(), nullable=False),
        sa.Column("panel_key", sa.String(64), nullable=False, server_default=""),
        sa.Column("book_name", sa.String(512), nullable=False, server_default=""),
        sa.Column("drama_type", sa.String(16), nullable=False, server_default=""),
        sa.Column("channel", sa.String(64), nullable=False, server_default=""),
        sa.Column("publish_date", sa.Date(), nullable=True),
        sa.Column("pitcher_ids", int_array, nullable=False),
        sa.Column("pitcher_names", text_array, nullable=False),
        sa.Column("department_names", text_array, nullable=False),
        sa.Column("bid_types", text_array, nullable=False),
        sa.Column("panel_names", text_array, nullable=False),
        sa.Column("costed_promotion_ids", big_array, nullable=False),
        *_manhua_metrics(),
        sa.UniqueConstraint("charge_mode", "stat_date", "series_id", "panel_key", name="uq_report_manhua_drama_day"),
    )
    op.create_index("ix_report_manhua_drama_day_range", "report_manhua_drama_day", ["charge_mode", "stat_date"])

    def owned() -> list[sa.Column]:
        return [
            sa.Column("stat_date", sa.Date(), nullable=False),
            sa.Column("charge_mode", sa.String(8), nullable=False),
            sa.Column("project_name", sa.Text(), nullable=False, server_default=""),
            sa.Column("series_id", sa.Integer(), nullable=False),
            sa.Column("book_name", sa.String(512), nullable=False, server_default=""),
            sa.Column("pitcher_id", sa.Integer(), nullable=False),
            sa.Column("pitcher_name", sa.String(64), nullable=False, server_default=""),
            sa.Column("department_name", sa.String(128), nullable=False, server_default=""),
            sa.Column("bid_type", sa.String(16), nullable=False, server_default=""),
            sa.Column("drama_type", sa.String(16), nullable=False, server_default=""),
            sa.Column("channel", sa.String(64), nullable=False, server_default=""),
            sa.Column("panel", sa.String(64), nullable=False, server_default=""),
            sa.Column("publish_date", sa.Date(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("first_cost_time", sa.String(64), nullable=True),
            sa.Column("project_budget", sa.Numeric(12, 2), nullable=True),
            sa.Column("roi_goal", sa.Numeric(10, 3), nullable=True),
            *_manhua_metrics(),
        ]

    op.create_table(
        "report_manhua_project_day",
        *_common(),
        sa.Column("project_id", sa.BigInteger(), nullable=False),
        *owned(),
        sa.UniqueConstraint("stat_date", "project_id", name="uq_report_manhua_project_day"),
    )
    op.create_index(
        "ix_report_manhua_project_day_owner",
        "report_manhua_project_day",
        ["charge_mode", "pitcher_id", "stat_date"],
    )
    op.create_table(
        "report_manhua_promotion_day",
        *_common(),
        sa.Column("promotion_id", sa.BigInteger(), nullable=False),
        sa.Column("promotion_name", sa.Text(), nullable=False, server_default=""),
        sa.Column("project_id", sa.BigInteger(), nullable=False),
        *owned(),
        sa.UniqueConstraint("stat_date", "promotion_id", name="uq_report_manhua_promotion_day"),
    )
    op.create_index(
        "ix_report_manhua_promotion_day_owner",
        "report_manhua_promotion_day",
        ["charge_mode", "pitcher_id", "stat_date"],
    )
    op.create_table(
        "report_uni_drama_day",
        *_common(),
        sa.Column("stat_date", sa.Date(), nullable=False),
        sa.Column("series_id", sa.Integer(), nullable=False),
        sa.Column("book_name", sa.String(512), nullable=False, server_default=""),
        sa.Column("platform_name", sa.String(64), nullable=False, server_default=""),
        sa.Column("pitcher_ids", int_array, nullable=False),
        *_uni_metrics(),
        sa.UniqueConstraint("stat_date", "series_id", name="uq_report_uni_drama_day"),
    )
    op.create_index("ix_report_uni_drama_day_date", "report_uni_drama_day", ["stat_date"])
    op.create_table(
        "report_uni_pitcher_drama_day",
        *_common(),
        sa.Column("stat_date", sa.Date(), nullable=False),
        sa.Column("pitcher_id", sa.Integer(), nullable=False),
        sa.Column("pitcher_name", sa.String(64), nullable=False, server_default=""),
        sa.Column("series_id", sa.Integer(), nullable=False),
        sa.Column("book_name", sa.String(512), nullable=False, server_default=""),
        sa.Column("platform_name", sa.String(64), nullable=False, server_default=""),
        *_uni_metrics(),
        sa.UniqueConstraint("stat_date", "pitcher_id", "series_id", name="uq_report_uni_pitcher_drama_day"),
    )
    op.create_index(
        "ix_report_uni_pitcher_drama_day_owner",
        "report_uni_pitcher_drama_day",
        ["pitcher_id", "stat_date"],
    )
    op.create_table(
        "report_uni_pitcher_day",
        *_common(),
        sa.Column("stat_date", sa.Date(), nullable=False),
        sa.Column("pitcher_id", sa.Integer(), nullable=False),
        sa.Column("pitcher_name", sa.String(64), nullable=False, server_default=""),
        *_uni_metrics(),
        sa.UniqueConstraint("stat_date", "pitcher_id", name="uq_report_uni_pitcher_day"),
    )
    op.create_index("ix_report_uni_pitcher_day_owner", "report_uni_pitcher_day", ["pitcher_id", "stat_date"])
    op.create_table(
        "report_uni_group_day",
        *_common(),
        sa.Column("stat_date", sa.Date(), nullable=False),
        sa.Column("department_id", sa.Integer(), nullable=False),
        sa.Column("department_name", sa.String(128), nullable=False, server_default=""),
        *_uni_metrics(),
        sa.UniqueConstraint("stat_date", "department_id", name="uq_report_uni_group_day"),
    )
    op.create_index("ix_report_uni_group_day_dept", "report_uni_group_day", ["department_id", "stat_date"])


def downgrade() -> None:
    for name in (
        "report_uni_group_day",
        "report_uni_pitcher_day",
        "report_uni_pitcher_drama_day",
        "report_uni_drama_day",
        "report_manhua_promotion_day",
        "report_manhua_project_day",
        "report_manhua_drama_day",
    ):
        op.drop_table(name)
