"""标准模板补版位、定向、项目预算、商品策略、广告状态、抖音号、主图和标题模式。

Revision ID: 20261008_04
Revises: 20261008_03
Create Date: 2026-10-08

标准行可以写 project_budget。roi_coefficient、aigc_dynamic_creative、title_select_mode 仍只给全域。
标准标题选择写 standard_title_select_mode。新列在全域行上必须为空。
草稿上的版位、项目预算、商品库、抖音号可以留空，确认提交时用模板。
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20261008_04"
down_revision: Union[str, None] = "20261008_03"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

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
    "AND (schedule_time IS NULL OR (char_length(schedule_time) = 336 AND schedule_time ~ '^[01]*$')) "
    "AND char_length(ad_source) BETWEEN 1 AND 100 "
    "AND char_length(product_name) BETWEEN 1 AND 20 "
    "AND cardinality(selling_points) <= 10 "
    "AND cardinality(call_to_action_buttons) <= 10 "
    "AND (roi_goal IS NULL OR (roi_goal >= 0 AND roi_goal <= 9999.999)) "
    "AND videos_per_ad BETWEEN 1 AND 30 "
    "AND titles_per_ad BETWEEN 1 AND 10"
)
_EXTRAS = (
    "(placement IS NULL OR placement IN ('aweme', 'aweme_feed', 'universal')) "
    "AND (district IS NULL OR district IN ('NONE', 'REGION')) "
    "AND (district IS DISTINCT FROM 'NONE' OR city_codes IS NULL OR cardinality(city_codes) = 0) "
    "AND (district IS DISTINCT FROM 'REGION' OR (city_codes IS NOT NULL AND cardinality(city_codes) > 0)) "
    "AND (project_budget IS NULL OR (project_budget > 0 AND project_budget <= 99999999.99)) "
    "AND (product_select IS NULL OR product_select IN ('this_series', 'other_series', 'manual')) "
    "AND ((product_library_id IS NULL AND product_select IS NULL) "
    "OR (product_library_id IS NOT NULL AND product_select IS NOT NULL)) "
    "AND (promotion_operation IS NULL OR promotion_operation IN ('ENABLE', 'DISABLE')) "
    "AND (product_image_id IS NULL OR (product_image_id LIKE 'img-%' AND char_length(product_image_id) BETWEEN 5 AND 64)) "
    "AND (standard_title_select_mode IS NULL OR standard_title_select_mode IN ('manual', 'auto'))"
)
_UNI_EXTRAS_EMPTY = (
    "placement IS NULL "
    "AND district IS NULL "
    "AND city_codes IS NULL "
    "AND product_library_id IS NULL "
    "AND product_select IS NULL "
    "AND material_boost IS NULL "
    "AND promotion_operation IS NULL "
    "AND douyin_account_id IS NULL "
    "AND product_image_id IS NULL "
    "AND standard_title_select_mode IS NULL"
)
_NEW_SHAPE = (
    "("
    "delivery_mode = 'standard' "
    "AND roi_coefficient IS NULL "
    "AND aigc_dynamic_creative IS NULL "
    "AND title_select_mode IS NULL "
    "AND ads_per_account BETWEEN 1 AND 100 "
    f"AND {_EXTRAS} "
    f"AND (({_LEGACY}) OR ({_FILLED}))"
    ") OR ("
    "delivery_mode = 'uni' "
    "AND project_budget IS NOT NULL AND project_budget > 0 AND project_budget <= 99999999.99 "
    "AND roi_coefficient IS NOT NULL AND roi_coefficient >= 0 AND roi_coefficient <= 9999.999 "
    "AND aigc_dynamic_creative IS NOT NULL "
    "AND title_select_mode IN ('manual', 'auto') "
    "AND ads_per_account IS NULL "
    "AND cardinality(bid_panels) = 0 "
    f"AND {_LEGACY} "
    f"AND {_UNI_EXTRAS_EMPTY}"
    ")"
)
_OLD_SHAPE = (
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
    op.add_column("delivery_template", sa.Column("placement", sa.String(16), nullable=True))
    op.add_column("delivery_template", sa.Column("district", sa.String(16), nullable=True))
    op.add_column(
        "delivery_template",
        sa.Column("city_codes", postgresql.ARRAY(sa.Integer()), nullable=True),
    )
    op.add_column("delivery_template", sa.Column("product_library_id", sa.Integer(), nullable=True))
    op.add_column("delivery_template", sa.Column("product_select", sa.String(16), nullable=True))
    op.add_column("delivery_template", sa.Column("material_boost", sa.Boolean(), nullable=True))
    op.add_column("delivery_template", sa.Column("promotion_operation", sa.String(16), nullable=True))
    op.add_column("delivery_template", sa.Column("douyin_account_id", sa.Integer(), nullable=True))
    op.add_column("delivery_template", sa.Column("product_image_id", sa.String(64), nullable=True))
    op.add_column("delivery_template", sa.Column("standard_title_select_mode", sa.String(16), nullable=True))
    op.create_foreign_key(
        "fk_delivery_template_product_library_id",
        "delivery_template",
        "product_library",
        ["product_library_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_foreign_key(
        "fk_delivery_template_douyin_account_id",
        "delivery_template",
        "douyin_account",
        ["douyin_account_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.drop_constraint("ck_delivery_template_mode_shape", "delivery_template", type_="check")
    op.create_check_constraint("ck_delivery_template_mode_shape", "delivery_template", _NEW_SHAPE)

    op.alter_column("delivery_task_draft", "placement", existing_type=sa.String(16), nullable=True)
    op.alter_column("delivery_task_draft", "project_budget", existing_type=sa.Numeric(12, 2), nullable=True)
    op.alter_column("delivery_task_draft", "product_library_id", existing_type=sa.Integer(), nullable=True)
    op.alter_column("delivery_task_draft", "douyin_account_id", existing_type=sa.Integer(), nullable=True)
    op.drop_constraint("ck_delivery_task_draft_placement", "delivery_task_draft", type_="check")
    op.create_check_constraint(
        "ck_delivery_task_draft_placement",
        "delivery_task_draft",
        "placement IS NULL OR placement IN ('aweme', 'aweme_feed', 'universal')",
    )
    op.drop_constraint("ck_delivery_task_draft_budget", "delivery_task_draft", type_="check")
    op.create_check_constraint(
        "ck_delivery_task_draft_budget",
        "delivery_task_draft",
        "(project_budget IS NULL OR project_budget > 0) AND ad_budget > 0",
    )


def downgrade() -> None:
    op.execute(
        "UPDATE delivery_task_draft AS d SET "
        "placement = COALESCE(d.placement, t.placement, 'aweme'), "
        "project_budget = COALESCE(d.project_budget, t.project_budget, 1), "
        "douyin_account_id = COALESCE(d.douyin_account_id, t.douyin_account_id), "
        "product_library_id = COALESCE(d.product_library_id, t.product_library_id) "
        "FROM delivery_template AS t WHERE t.id = d.template_id"
    )
    op.drop_constraint("ck_delivery_task_draft_budget", "delivery_task_draft", type_="check")
    op.create_check_constraint(
        "ck_delivery_task_draft_budget",
        "delivery_task_draft",
        "project_budget > 0 AND ad_budget > 0",
    )
    op.drop_constraint("ck_delivery_task_draft_placement", "delivery_task_draft", type_="check")
    op.create_check_constraint(
        "ck_delivery_task_draft_placement",
        "delivery_task_draft",
        "placement IN ('aweme', 'aweme_feed', 'universal')",
    )
    op.alter_column("delivery_task_draft", "douyin_account_id", existing_type=sa.Integer(), nullable=False)
    op.alter_column("delivery_task_draft", "product_library_id", existing_type=sa.Integer(), nullable=False)
    op.alter_column("delivery_task_draft", "project_budget", existing_type=sa.Numeric(12, 2), nullable=False)
    op.alter_column("delivery_task_draft", "placement", existing_type=sa.String(16), nullable=False)

    op.execute("UPDATE delivery_template SET project_budget = NULL WHERE delivery_mode = 'standard'")
    op.drop_constraint("ck_delivery_template_mode_shape", "delivery_template", type_="check")
    op.create_check_constraint("ck_delivery_template_mode_shape", "delivery_template", _OLD_SHAPE)
    op.drop_constraint("fk_delivery_template_douyin_account_id", "delivery_template", type_="foreignkey")
    op.drop_constraint("fk_delivery_template_product_library_id", "delivery_template", type_="foreignkey")
    op.drop_column("delivery_template", "standard_title_select_mode")
    op.drop_column("delivery_template", "product_image_id")
    op.drop_column("delivery_template", "douyin_account_id")
    op.drop_column("delivery_template", "promotion_operation")
    op.drop_column("delivery_template", "material_boost")
    op.drop_column("delivery_template", "product_select")
    op.drop_column("delivery_template", "product_library_id")
    op.drop_column("delivery_template", "city_codes")
    op.drop_column("delivery_template", "district")
    op.drop_column("delivery_template", "placement")
