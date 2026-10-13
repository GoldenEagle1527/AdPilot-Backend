"""报表小时快照：标准投放广告（BASIC_DATA）与全域项目（UNI_PROJECT_DATA）。

Revision ID: 20261013_10
Revises: 20261013_01
Create Date: 2026-10-13

报表页只读这两张表，不在请求里调巨量。比率字段（ROI、点击率、千展成本等）
漫剧侧不建列，按区间合计后再算；全域侧 all_roi_* 存巨量原值，跨行合计时报表用 GMV / 成本重算。
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20261013_10"
down_revision: Union[str, None] = "20261013_01"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _common() -> list[sa.Column]:
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


def _money(name: str, comment: str) -> sa.Column:
    return sa.Column(name, sa.Numeric(18, 2), nullable=False, comment=comment)


def _count(name: str, comment: str) -> sa.Column:
    return sa.Column(name, sa.BigInteger(), nullable=False, comment=comment)


def _ratio(name: str, comment: str) -> sa.Column:
    return sa.Column(name, sa.Numeric(14, 4), nullable=False, comment=comment)


def upgrade() -> None:
    op.create_table(
        "oe_delivery_report",
        *_common(),
        sa.Column("advertiser_id", sa.BigInteger(), nullable=False, comment="查询用的巨量广告主 id"),
        sa.Column("stat_time_hour", sa.String(length=64), nullable=False, comment="小时，北京时间 YYYY-MM-DD HH:MM:SS"),
        sa.Column("cdp_project_id", sa.BigInteger(), nullable=False, comment="项目 id"),
        sa.Column("cdp_project_name", sa.Text(), nullable=True, comment="项目名称"),
        sa.Column("cdp_promotion_id", sa.BigInteger(), nullable=False, comment="广告 id"),
        sa.Column("cdp_promotion_name", sa.Text(), nullable=True, comment="广告名称"),
        _money("stat_cost", "消耗，单位元"),
        _money("stat_pay_amount", "付费金额（回传时间）。漫剧报表的回收"),
        _money("attribution_game_in_app_ltv_1day", "当日付费金额"),
        _money("attribution_game_in_app_ltv_8days", "激活后七日付费金额"),
        _money("attribution_micro_game_0d_ltv", "小程序/小游戏当日 LTV"),
        _money("attribution_micro_game_7d_ltv", "小程序/小游戏激活后七日 LTV"),
        _count("show_cnt", "展示数"),
        _count("click_cnt", "点击数"),
        _count("convert_cnt", "转化数"),
        _count("active", "激活数"),
        sa.Column("synced_at", sa.DateTime(timezone=True), nullable=False, comment="本行写入时间"),
        sa.UniqueConstraint(
            "advertiser_id",
            "stat_time_hour",
            "cdp_project_id",
            "cdp_promotion_id",
            name="uq_oe_delivery_report_grain",
        ),
        comment="巨量广告小时报表（BASIC_DATA）。比率字段不落库。",
    )
    op.create_index(
        "ix_oe_delivery_report_hour_project", "oe_delivery_report", ["stat_time_hour", "cdp_project_id"]
    )
    op.create_index(
        "ix_oe_delivery_report_promotion_hour", "oe_delivery_report", ["cdp_promotion_id", "stat_time_hour"]
    )
    op.create_table(
        "oe_uni_project_report",
        *_common(),
        sa.Column("advertiser_id", sa.BigInteger(), nullable=False, comment="查询用的巨量广告主 id"),
        sa.Column("stat_time_hour", sa.String(length=64), nullable=False, comment="小时，北京时间 YYYY-MM-DD HH:MM:SS"),
        sa.Column("cdp_project_id", sa.BigInteger(), nullable=False, comment="项目 id"),
        sa.Column("cdp_project_name", sa.Text(), nullable=True, comment="项目名称"),
        _money("all_stat_cost_trend", "全域消耗"),
        _money("all_stat_total_cost_trend", "全域成本"),
        _money("all_gmv_trend", "全域 GMV"),
        _money("all_billing_gmv_0day_trend", "当日全域 GMV（计费时间）"),
        _money("all_billing_gmv_24h_trend", "24 小时全域 GMV（计费时间）"),
        _money("all_billing_gmv_3days_trend", "三日全域 GMV（计费时间）。合计三日 ROI 用"),
        _money("all_income_trend", "全域收入"),
        _money("all_income_0day_trend", "当日全域收入（计费时间）"),
        _money("all_pay_amount_income_trend", "付费收入"),
        _money("all_micro_game_income_trend", "变现收入"),
        _ratio("all_roi_trend", "全域 ROI，巨量原值"),
        _ratio("all_roi_24h_trend", "全域 24 小时 ROI，巨量原值"),
        _ratio("all_roi_0day_trend", "全域当日 ROI，巨量原值"),
        _ratio("all_roi_3days_trend", "全域三日 ROI，巨量原值"),
        _count("all_show_cnt_trend", "全域展示数"),
        _count("all_click_cnt_trend", "全域点击数"),
        sa.Column("synced_at", sa.DateTime(timezone=True), nullable=False, comment="本行写入时间"),
        sa.UniqueConstraint(
            "advertiser_id", "stat_time_hour", "cdp_project_id", name="uq_oe_uni_project_report_grain"
        ),
        comment="巨量全域 ROI 项目小时报表（UNI_PROJECT_DATA）。",
    )
    op.create_index(
        "ix_oe_uni_project_report_hour_project", "oe_uni_project_report", ["stat_time_hour", "cdp_project_id"]
    )


def downgrade() -> None:
    op.drop_index("ix_oe_uni_project_report_hour_project", table_name="oe_uni_project_report")
    op.drop_table("oe_uni_project_report")
    op.drop_index("ix_oe_delivery_report_promotion_hour", table_name="oe_delivery_report")
    op.drop_index("ix_oe_delivery_report_hour_project", table_name="oe_delivery_report")
    op.drop_table("oe_delivery_report")
