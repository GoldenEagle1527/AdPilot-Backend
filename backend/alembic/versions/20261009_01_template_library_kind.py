"""标准模板改记商品库类型，不再要求选中某一行商品库。

Revision ID: 20261009_01
Revises: 20261008_04
Create Date: 2026-10-09

product_library_id 保持可空，写入接口不再要求客户端传它。
新增 library_kind：video 视频库、novel 小说库，可空。
商品库类型和商品选择各自可空，不再成对。
确认提交按类型解析投手的标准库或组织兜底库，不读模板上的 product_library_id。
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20261009_01"
down_revision: Union[str, None] = "20261008_04"
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
    "AND (library_kind IS NULL OR library_kind IN ('video', 'novel')) "
    "AND (product_select IS NULL OR product_select IN ('this_series', 'other_series', 'manual')) "
    "AND (promotion_operation IS NULL OR promotion_operation IN ('ENABLE', 'DISABLE')) "
    "AND (product_image_id IS NULL OR (product_image_id LIKE 'img-%' AND char_length(product_image_id) BETWEEN 5 AND 64)) "
    "AND (standard_title_select_mode IS NULL OR standard_title_select_mode IN ('manual', 'auto'))"
)
_UNI_EMPTY = (
    "placement IS NULL "
    "AND district IS NULL "
    "AND city_codes IS NULL "
    "AND product_library_id IS NULL "
    "AND library_kind IS NULL "
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
    f"AND {_UNI_EMPTY}"
    ")"
)
_OLD_EXTRAS = (
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
_OLD_UNI_EMPTY = (
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
_OLD_SHAPE = (
    "("
    "delivery_mode = 'standard' "
    "AND roi_coefficient IS NULL "
    "AND aigc_dynamic_creative IS NULL "
    "AND title_select_mode IS NULL "
    "AND ads_per_account BETWEEN 1 AND 100 "
    f"AND {_OLD_EXTRAS} "
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
    f"AND {_OLD_UNI_EMPTY}"
    ")"
)


def upgrade() -> None:
    op.add_column(
        "delivery_template",
        sa.Column("library_kind", sa.String(length=16), nullable=True, comment="video 视频库、novel 小说库"),
    )
    op.drop_constraint("ck_delivery_template_mode_shape", "delivery_template", type_="check")
    op.create_check_constraint("ck_delivery_template_mode_shape", "delivery_template", _NEW_SHAPE)


def downgrade() -> None:
    op.drop_constraint("ck_delivery_template_mode_shape", "delivery_template", type_="check")
    op.execute(
        "UPDATE delivery_template SET product_select = NULL "
        "WHERE product_library_id IS NULL AND product_select IS NOT NULL"
    )
    op.create_check_constraint("ck_delivery_template_mode_shape", "delivery_template", _OLD_SHAPE)
    op.drop_column("delivery_template", "library_kind")
