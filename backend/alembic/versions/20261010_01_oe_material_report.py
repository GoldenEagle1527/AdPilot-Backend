"""素材小时报表：只存巨量自定义报表能直接取到的维度和指标。

Revision ID: 20261010_01
Revises: 20261009_06
Create Date: 2026-10-10

回收率、收益率、点击率、千次展示费用、点击单价、转化成本、转化率、
激活成本、激活 ARPU、盈亏、组平均 ROI 是中台自己算的，不建列。
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20261010_01"
down_revision: Union[str, None] = "20261009_06"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _common() -> list[sa.Column]:
    """和 BaseModel 对齐的公共列。"""
    return [
        sa.Column("id", sa.Integer(), sa.Identity(), primary_key=True, comment="库内自增主键"),
        sa.Column("is_deleted", sa.Integer(), nullable=False, server_default="0", comment="是否删除：0 否、1 是"),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True, comment="删除时间，未删为空"),
        sa.Column(
            "created_date",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
            comment="创建时间（北京）",
        ),
        sa.Column(
            "updated_date",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
            comment="更新时间（北京）",
        ),
    ]


def upgrade() -> None:
    op.create_table(
        "oe_material_report",
        *_common(),
        sa.Column("advertiser_id", sa.BigInteger(), nullable=False, comment="查询用的巨量广告主 id"),
        sa.Column(
            "stat_time_hour",
            sa.String(length=64),
            nullable=False,
            comment="时间。近 8 天为小时，更早的日期为天",
        ),
        sa.Column("material_id", sa.BigInteger(), nullable=False, comment="素材 id"),
        sa.Column("ad_platform_material_name", sa.Text(), nullable=True, comment="素材名称"),
        sa.Column("cdp_promotion_id", sa.BigInteger(), nullable=False, comment="广告 id"),
        sa.Column("cdp_promotion_name", sa.Text(), nullable=True, comment="广告名称"),
        sa.Column("cdp_project_id", sa.BigInteger(), nullable=False, comment="项目 id"),
        sa.Column("cdp_project_name", sa.Text(), nullable=True, comment="项目名称"),
        sa.Column("stat_cost", sa.Numeric(18, 2), nullable=False, comment="消耗，单位元"),
        sa.Column(
            "attribution_billing_game_in_app_ltv_1day",
            sa.Numeric(18, 2),
            nullable=False,
            comment="广告收益(当日)，计费当日付费金额",
        ),
        sa.Column(
            "stat_pay_amount",
            sa.Numeric(18, 2),
            nullable=False,
            comment="付费金额。广告总收益和回收金额都是这个字段",
        ),
        sa.Column("show_cnt", sa.BigInteger(), nullable=False, comment="展示数"),
        sa.Column("click_cnt", sa.BigInteger(), nullable=False, comment="点击数"),
        sa.Column("convert_cnt", sa.BigInteger(), nullable=False, comment="转化数"),
        sa.Column("active", sa.BigInteger(), nullable=False, comment="激活数"),
        sa.Column("game_addiction", sa.BigInteger(), nullable=False, comment="关键行为数"),
        sa.Column("synced_at", sa.DateTime(timezone=True), nullable=False, comment="本行写入时间"),
        sa.UniqueConstraint(
            "advertiser_id",
            "stat_time_hour",
            "material_id",
            "cdp_promotion_id",
            "cdp_project_id",
            name="uq_oe_material_report_grain",
        ),
        comment="巨量素材小时报表。公式字段不落库。",
    )
    op.create_index(
        "ix_oe_material_report_advertiser_hour",
        "oe_material_report",
        ["advertiser_id", "stat_time_hour"],
    )


def downgrade() -> None:
    op.drop_index("ix_oe_material_report_advertiser_hour", table_name="oe_material_report")
    op.drop_table("oe_material_report")
