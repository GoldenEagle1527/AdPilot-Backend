"""全域模板可以保存用户定向：性别、年龄、地域和城市。

Revision ID: 20261012_01
Revises: 20261010_02
Create Date: 2026-10-12

列本来就在 delivery_template 上。这一版只放开全域行的检查，不限地域仍不能带城市。
"""

from typing import Sequence, Union

from alembic import op

revision: str = "20261012_01"
down_revision: Union[str, None] = "20261010_02"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# 放开之前，全域行的性别、年龄、地域必须为空。
_OLD_UNI_EXTRAS = (
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
    "AND standard_title_select_mode IS NULL "
    "AND gender IS NULL "
    "AND age_bands IS NULL"
)


def _previous_shape() -> str:
    """用当前模型里没改的片段，拼回放开定向之前的检查。"""
    from app.modules.standard_delivery.model import (
        _STANDARD_EXTRAS,
        _STANDARD_FILLED,
        _STANDARD_LEGACY,
        _UNI_PAGE,
    )

    return (
        "("
        "delivery_mode = 'standard' "
        "AND roi_coefficient IS NULL "
        "AND aigc_dynamic_creative IS NULL "
        "AND title_select_mode IS NULL "
        "AND ads_per_account BETWEEN 1 AND 100 "
        f"AND {_STANDARD_EXTRAS} "
        f"AND (({_STANDARD_LEGACY}) OR ({_STANDARD_FILLED}))"
        ") OR ("
        "delivery_mode = 'uni' "
        "AND project_budget IS NOT NULL AND project_budget > 0 AND project_budget <= 99999999.99 "
        "AND roi_coefficient IS NOT NULL AND roi_coefficient >= 0 AND roi_coefficient <= 9999.999 "
        "AND aigc_dynamic_creative IS NOT NULL "
        "AND title_select_mode IN ('manual', 'auto') "
        "AND ads_per_account IS NULL "
        "AND cardinality(bid_panels) = 0 "
        f"AND ({_UNI_PAGE}) "
        f"AND {_OLD_UNI_EXTRAS}"
        ")"
    )


def upgrade() -> None:
    from app.modules.standard_delivery.model import _TEMPLATE_SHAPE

    op.drop_constraint("ck_delivery_template_mode_shape", "delivery_template", type_="check")
    op.create_check_constraint("ck_delivery_template_mode_shape", "delivery_template", _TEMPLATE_SHAPE)


def downgrade() -> None:
    op.drop_constraint("ck_delivery_template_mode_shape", "delivery_template", type_="check")
    op.create_check_constraint("ck_delivery_template_mode_shape", "delivery_template", _previous_shape())
