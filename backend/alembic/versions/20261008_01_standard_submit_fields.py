"""标准模板和草稿补确认提交要用的字段。

Revision ID: 20261008_01
Revises: 20260930_04
Create Date: 2026-10-08

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "20261008_01"
down_revision: Union[str, None] = "20260930_04"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_OLD_SHAPE = (
    "("
    "delivery_mode = 'standard' "
    "AND project_budget IS NULL "
    "AND roi_coefficient IS NULL "
    "AND aigc_dynamic_creative IS NULL "
    "AND title_select_mode IS NULL "
    "AND ads_per_account BETWEEN 1 AND 100"
    ") OR ("
    "delivery_mode = 'uni' "
    "AND project_budget IS NOT NULL AND project_budget > 0 AND project_budget <= 99999999.99 "
    "AND roi_coefficient IS NOT NULL AND roi_coefficient >= 0 AND roi_coefficient <= 9999.999 "
    "AND aigc_dynamic_creative IS NOT NULL "
    "AND title_select_mode IN ('manual', 'auto') "
    "AND ads_per_account IS NULL "
    "AND cardinality(bid_panels) = 0"
    ")"
)

_LEGACY = (
    "ocean_delivery_mode IS NULL "
    "AND bid_type IS NULL "
    "AND schedule_type IS NULL "
    "AND schedule_start_date IS NULL "
    "AND schedule_end_date IS NULL "
    "AND schedule_time IS NULL "
    "AND ad_source IS NULL "
    "AND product_name IS NULL "
    "AND cardinality(selling_points) = 0 "
    "AND cardinality(call_to_action_buttons) = 0 "
    "AND roi_goal IS NULL "
    "AND videos_per_ad IS NULL "
    "AND titles_per_ad IS NULL"
)
_FILLED = (
    "ocean_delivery_mode IN ('MANUAL', 'PROCEDURAL') "
    "AND bid_type IN ('CUSTOM', 'NO_BID') "
    "AND ("
    "(schedule_type = 'SCHEDULE_FROM_NOW' AND schedule_start_date IS NULL AND schedule_end_date IS NULL) "
    "OR (schedule_type = 'SCHEDULE_START_END' AND schedule_start_date IS NOT NULL "
    "AND schedule_end_date IS NOT NULL AND schedule_start_date <= schedule_end_date)"
    ") "
    "AND (schedule_time IS NULL OR schedule_time ~ '^[01]{336}$') "
    "AND char_length(ad_source) BETWEEN 1 AND 100 "
    "AND char_length(product_name) BETWEEN 1 AND 20 "
    "AND cardinality(selling_points) <= 10 "
    "AND cardinality(call_to_action_buttons) <= 10 "
    "AND (roi_goal IS NULL OR (roi_goal >= 0 AND roi_goal <= 9999.999)) "
    "AND videos_per_ad BETWEEN 1 AND 30 "
    "AND titles_per_ad BETWEEN 1 AND 10"
)
_NEW_SHAPE = (
    "("
    "delivery_mode = 'standard' "
    "AND project_budget IS NULL "
    "AND roi_coefficient IS NULL "
    "AND aigc_dynamic_creative IS NULL "
    "AND title_select_mode IS NULL "
    "AND ads_per_account BETWEEN 1 AND 100 "
    f"AND (({_LEGACY}) OR ({_FILLED}))"
    ") OR ("
    "delivery_mode = 'uni' "
    "AND project_budget IS NOT NULL AND project_budget > 0 AND project_budget <= 99999999.99 "
    "AND roi_coefficient IS NOT NULL AND roi_coefficient >= 0 AND roi_coefficient <= 9999.999 "
    "AND aigc_dynamic_creative IS NOT NULL "
    "AND title_select_mode IN ('manual', 'auto') "
    "AND ads_per_account IS NULL "
    "AND cardinality(bid_panels) = 0 "
    f"AND {_LEGACY}"
    ")"
)


def upgrade() -> None:
    op.add_column("delivery_template", sa.Column("ocean_delivery_mode", sa.String(16), nullable=True))
    op.add_column("delivery_template", sa.Column("bid_type", sa.String(16), nullable=True))
    op.add_column("delivery_template", sa.Column("schedule_type", sa.String(32), nullable=True))
    op.add_column("delivery_template", sa.Column("schedule_start_date", sa.Date(), nullable=True))
    op.add_column("delivery_template", sa.Column("schedule_end_date", sa.Date(), nullable=True))
    op.add_column("delivery_template", sa.Column("schedule_time", sa.String(336), nullable=True))
    op.add_column("delivery_template", sa.Column("ad_source", sa.String(100), nullable=True))
    op.add_column("delivery_template", sa.Column("product_name", sa.String(20), nullable=True))
    op.add_column(
        "delivery_template",
        sa.Column(
            "selling_points",
            postgresql.ARRAY(sa.String(20)),
            nullable=False,
            server_default=sa.text("ARRAY[]::varchar[]"),
        ),
    )
    op.add_column(
        "delivery_template",
        sa.Column(
            "call_to_action_buttons",
            postgresql.ARRAY(sa.String(20)),
            nullable=False,
            server_default=sa.text("ARRAY[]::varchar[]"),
        ),
    )
    op.add_column("delivery_template", sa.Column("roi_goal", sa.Numeric(10, 3), nullable=True))
    op.add_column("delivery_template", sa.Column("videos_per_ad", sa.Integer(), nullable=True))
    op.add_column("delivery_template", sa.Column("titles_per_ad", sa.Integer(), nullable=True))
    op.drop_constraint("ck_delivery_template_mode_shape", "delivery_template", type_="check")
    op.create_check_constraint("ck_delivery_template_mode_shape", "delivery_template", _NEW_SHAPE)

    op.add_column("delivery_task_draft", sa.Column("album_url", sa.String(2048), nullable=True))
    op.add_column("delivery_task_draft", sa.Column("project_operation", sa.String(16), nullable=True))
    op.add_column("delivery_task_draft", sa.Column("promotion_operation", sa.String(16), nullable=True))
    op.create_check_constraint(
        "ck_delivery_task_draft_project_operation",
        "delivery_task_draft",
        "project_operation IS NULL OR project_operation IN ('ENABLE', 'DISABLE')",
    )
    op.create_check_constraint(
        "ck_delivery_task_draft_promotion_operation",
        "delivery_task_draft",
        "promotion_operation IS NULL OR promotion_operation IN ('ENABLE', 'DISABLE')",
    )
    op.alter_column("oe_product", "file_url", existing_type=sa.String(2048), nullable=True)


def downgrade() -> None:
    op.execute("UPDATE oe_product SET file_url = '' WHERE file_url IS NULL")
    op.alter_column("oe_product", "file_url", existing_type=sa.String(2048), nullable=False)
    op.drop_constraint("ck_delivery_task_draft_promotion_operation", "delivery_task_draft", type_="check")
    op.drop_constraint("ck_delivery_task_draft_project_operation", "delivery_task_draft", type_="check")
    op.drop_column("delivery_task_draft", "promotion_operation")
    op.drop_column("delivery_task_draft", "project_operation")
    op.drop_column("delivery_task_draft", "album_url")

    op.drop_constraint("ck_delivery_template_mode_shape", "delivery_template", type_="check")
    op.drop_column("delivery_template", "titles_per_ad")
    op.drop_column("delivery_template", "videos_per_ad")
    op.drop_column("delivery_template", "roi_goal")
    op.drop_column("delivery_template", "call_to_action_buttons")
    op.drop_column("delivery_template", "selling_points")
    op.drop_column("delivery_template", "product_name")
    op.drop_column("delivery_template", "ad_source")
    op.drop_column("delivery_template", "schedule_time")
    op.drop_column("delivery_template", "schedule_end_date")
    op.drop_column("delivery_template", "schedule_start_date")
    op.drop_column("delivery_template", "schedule_type")
    op.drop_column("delivery_template", "bid_type")
    op.drop_column("delivery_template", "ocean_delivery_mode")
    op.create_check_constraint("ck_delivery_template_mode_shape", "delivery_template", _OLD_SHAPE)
