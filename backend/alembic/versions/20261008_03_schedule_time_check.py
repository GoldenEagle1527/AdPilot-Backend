"""投放时段检查改成长度加 0/1 模式。

Revision ID: 20261008_03
Revises: 20261008_02
Create Date: 2026-10-08

PostgreSQL 正则重复次数上限是 255，`^[01]{336}$` 在插入时会报
invalid repetition count。非空 schedule_time 改为恰好 336 个字符且只含 0/1。
空值仍表示不限。
"""
from typing import Sequence, Union

from alembic import op

revision: str = "20261008_03"
down_revision: Union[str, None] = "20261008_02"
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


def _filled(schedule_time_check: str) -> str:
    """标准行写满时的形状。只换时段检查。"""
    return (
        "ocean_delivery_mode IN ('MANUAL', 'PROCEDURAL') "
        "AND bid_type IN ('CUSTOM', 'NO_BID') "
        "AND ("
        "(schedule_type = 'SCHEDULE_FROM_NOW' AND schedule_start_date IS NULL AND schedule_end_date IS NULL) "
        "OR (schedule_type = 'SCHEDULE_START_END' AND schedule_start_date IS NOT NULL "
        "AND schedule_end_date IS NOT NULL AND schedule_start_date <= schedule_end_date)"
        ") "
        f"AND (schedule_time IS NULL OR ({schedule_time_check})) "
        "AND char_length(ad_source) BETWEEN 1 AND 100 "
        "AND char_length(product_name) BETWEEN 1 AND 20 "
        "AND cardinality(selling_points) <= 10 "
        "AND cardinality(call_to_action_buttons) <= 10 "
        "AND (roi_goal IS NULL OR (roi_goal >= 0 AND roi_goal <= 9999.999)) "
        "AND videos_per_ad BETWEEN 1 AND 30 "
        "AND titles_per_ad BETWEEN 1 AND 10"
    )


def _shape(schedule_time_check: str) -> str:
    """整条 ck_delivery_template_mode_shape。"""
    filled = _filled(schedule_time_check)
    return (
        "("
        "delivery_mode = 'standard' "
        "AND project_budget IS NULL "
        "AND roi_coefficient IS NULL "
        "AND aigc_dynamic_creative IS NULL "
        "AND title_select_mode IS NULL "
        "AND ads_per_account BETWEEN 1 AND 100 "
        f"AND (({_LEGACY}) OR ({filled}))"
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


# {336} 超过 PostgreSQL 重复次数上限，只留在降级里，还原改之前的检查。
_OLD_SCHEDULE = "schedule_time ~ '^[01]{336}$'"
_NEW_SCHEDULE = "char_length(schedule_time) = 336 AND schedule_time ~ '^[01]*$'"


def upgrade() -> None:
    op.drop_constraint("ck_delivery_template_mode_shape", "delivery_template", type_="check")
    op.create_check_constraint(
        "ck_delivery_template_mode_shape",
        "delivery_template",
        _shape(_NEW_SCHEDULE),
    )


def downgrade() -> None:
    op.drop_constraint("ck_delivery_template_mode_shape", "delivery_template", type_="check")
    op.create_check_constraint(
        "ck_delivery_template_mode_shape",
        "delivery_template",
        _shape(_OLD_SCHEDULE),
    )
