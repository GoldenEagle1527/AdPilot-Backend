"""接口同形的日表。小时任务用原始快照刷这几张表，列表只读这里。

剧目、项目、计划的日期是一段区间、对外合成一行，所以日表按天存可加指标，
读取时只把区间内的日行相加。全域列表本身就是一天一行，读取时按日期筛选，不再汇总。
趋势和时速仍读小时原始表，弹框要的就是小时。
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import BaseModel

_TS = DateTime(timezone=True)


class ReportManhuaDramaDay(BaseModel):
    """漫剧剧目日行。付费按面板拆，免费 panel_key 为空。"""

    __tablename__ = "report_manhua_drama_day"
    __table_args__ = (
        UniqueConstraint(
            "charge_mode",
            "stat_date",
            "series_id",
            "panel_key",
            name="uq_report_manhua_drama_day",
        ),
        Index("ix_report_manhua_drama_day_range", "charge_mode", "stat_date"),
        {"comment": "漫剧剧目日表。列表把区间内的行相加，不再扫小时明细。"},
    )

    stat_date: Mapped[date] = mapped_column(Date, nullable=False, comment="统计日，北京时间")
    charge_mode: Mapped[str] = mapped_column(String(8), nullable=False, comment="IAP 或 IAA")
    series_id: Mapped[int] = mapped_column(Integer, nullable=False, comment="短剧 id")
    panel_key: Mapped[str] = mapped_column(
        String(64), nullable=False, default="", server_default="", comment="付费面板。免费为空串"
    )
    book_name: Mapped[str] = mapped_column(String(512), nullable=False, default="", server_default="")
    drama_type: Mapped[str] = mapped_column(String(16), nullable=False, default="", server_default="")
    channel: Mapped[str] = mapped_column(String(64), nullable=False, default="", server_default="")
    publish_date: Mapped[date | None] = mapped_column(Date, nullable=True, comment="短剧上线日")
    pitcher_ids: Mapped[list[int]] = mapped_column(ARRAY(Integer), nullable=False)
    pitcher_names: Mapped[list[str]] = mapped_column(ARRAY(Text), nullable=False)
    department_names: Mapped[list[str]] = mapped_column(ARRAY(Text), nullable=False)
    bid_types: Mapped[list[str]] = mapped_column(ARRAY(Text), nullable=False)
    panel_names: Mapped[list[str]] = mapped_column(ARRAY(Text), nullable=False)
    costed_promotion_ids: Mapped[list[int]] = mapped_column(ARRAY(BigInteger), nullable=False)
    stat_cost: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    stat_pay_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    attribution_game_in_app_ltv_1day: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    attribution_game_in_app_ltv_8days: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    attribution_micro_game_0d_ltv: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    attribution_micro_game_7d_ltv: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    show_cnt: Mapped[int] = mapped_column(BigInteger, nullable=False)
    click_cnt: Mapped[int] = mapped_column(BigInteger, nullable=False)
    convert_cnt: Mapped[int] = mapped_column(BigInteger, nullable=False)
    active: Mapped[int] = mapped_column(BigInteger, nullable=False)


class ReportManhuaProjectDay(BaseModel):
    """漫剧项目日行。一个巨量项目一天一行。"""

    __tablename__ = "report_manhua_project_day"
    __table_args__ = (
        UniqueConstraint("stat_date", "project_id", name="uq_report_manhua_project_day"),
        Index("ix_report_manhua_project_day_owner", "charge_mode", "pitcher_id", "stat_date"),
        {"comment": "漫剧项目日表。列表按项目把区间内的日行相加。"},
    )

    stat_date: Mapped[date] = mapped_column(Date, nullable=False)
    charge_mode: Mapped[str] = mapped_column(String(8), nullable=False)
    project_id: Mapped[int] = mapped_column(BigInteger, nullable=False, comment="巨量项目 id")
    project_name: Mapped[str] = mapped_column(Text, nullable=False, default="", server_default="")
    series_id: Mapped[int] = mapped_column(Integer, nullable=False)
    book_name: Mapped[str] = mapped_column(String(512), nullable=False, default="", server_default="")
    pitcher_id: Mapped[int] = mapped_column(Integer, nullable=False)
    pitcher_name: Mapped[str] = mapped_column(String(64), nullable=False, default="", server_default="")
    department_name: Mapped[str] = mapped_column(String(128), nullable=False, default="", server_default="")
    bid_type: Mapped[str] = mapped_column(String(16), nullable=False, default="", server_default="")
    drama_type: Mapped[str] = mapped_column(String(16), nullable=False, default="", server_default="")
    channel: Mapped[str] = mapped_column(String(64), nullable=False, default="", server_default="")
    panel: Mapped[str] = mapped_column(String(64), nullable=False, default="", server_default="")
    publish_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    created_at: Mapped[datetime | None] = mapped_column(_TS, nullable=True, comment="中台记下这个项目的时间")
    first_cost_time: Mapped[str | None] = mapped_column(String(64), nullable=True, comment="第一次有消耗的小时原串")
    project_budget: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    roi_goal: Mapped[Decimal | None] = mapped_column(Numeric(10, 3), nullable=True)
    stat_cost: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    stat_pay_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    attribution_game_in_app_ltv_1day: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    attribution_game_in_app_ltv_8days: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    attribution_micro_game_0d_ltv: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    attribution_micro_game_7d_ltv: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    show_cnt: Mapped[int] = mapped_column(BigInteger, nullable=False)
    click_cnt: Mapped[int] = mapped_column(BigInteger, nullable=False)
    convert_cnt: Mapped[int] = mapped_column(BigInteger, nullable=False)
    active: Mapped[int] = mapped_column(BigInteger, nullable=False)


class ReportManhuaPromotionDay(BaseModel):
    """漫剧计划日行。一条广告一天一行。"""

    __tablename__ = "report_manhua_promotion_day"
    __table_args__ = (
        UniqueConstraint("stat_date", "promotion_id", name="uq_report_manhua_promotion_day"),
        Index("ix_report_manhua_promotion_day_owner", "charge_mode", "pitcher_id", "stat_date"),
        {"comment": "漫剧计划日表。列表按广告把区间内的日行相加。"},
    )

    stat_date: Mapped[date] = mapped_column(Date, nullable=False)
    charge_mode: Mapped[str] = mapped_column(String(8), nullable=False)
    promotion_id: Mapped[int] = mapped_column(BigInteger, nullable=False, comment="巨量广告 id")
    promotion_name: Mapped[str] = mapped_column(Text, nullable=False, default="", server_default="")
    project_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    project_name: Mapped[str] = mapped_column(Text, nullable=False, default="", server_default="")
    series_id: Mapped[int] = mapped_column(Integer, nullable=False)
    book_name: Mapped[str] = mapped_column(String(512), nullable=False, default="", server_default="")
    pitcher_id: Mapped[int] = mapped_column(Integer, nullable=False)
    pitcher_name: Mapped[str] = mapped_column(String(64), nullable=False, default="", server_default="")
    department_name: Mapped[str] = mapped_column(String(128), nullable=False, default="", server_default="")
    bid_type: Mapped[str] = mapped_column(String(16), nullable=False, default="", server_default="")
    drama_type: Mapped[str] = mapped_column(String(16), nullable=False, default="", server_default="")
    channel: Mapped[str] = mapped_column(String(64), nullable=False, default="", server_default="")
    panel: Mapped[str] = mapped_column(String(64), nullable=False, default="", server_default="")
    publish_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    created_at: Mapped[datetime | None] = mapped_column(_TS, nullable=True)
    first_cost_time: Mapped[str | None] = mapped_column(String(64), nullable=True)
    project_budget: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    roi_goal: Mapped[Decimal | None] = mapped_column(Numeric(10, 3), nullable=True)
    stat_cost: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    stat_pay_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    attribution_game_in_app_ltv_1day: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    attribution_game_in_app_ltv_8days: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    attribution_micro_game_0d_ltv: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    attribution_micro_game_7d_ltv: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    show_cnt: Mapped[int] = mapped_column(BigInteger, nullable=False)
    click_cnt: Mapped[int] = mapped_column(BigInteger, nullable=False)
    convert_cnt: Mapped[int] = mapped_column(BigInteger, nullable=False)
    active: Mapped[int] = mapped_column(BigInteger, nullable=False)


class ReportUniDramaDay(BaseModel):
    """全域短剧收益。一部剧一天一行，投手已合并。"""

    __tablename__ = "report_uni_drama_day"
    __table_args__ = (
        UniqueConstraint("stat_date", "series_id", name="uq_report_uni_drama_day"),
        Index("ix_report_uni_drama_day_date", "stat_date"),
        {"comment": "全域短剧收益日表。列表按日期筛选，不再汇总。"},
    )

    stat_date: Mapped[date] = mapped_column(Date, nullable=False)
    series_id: Mapped[int] = mapped_column(Integer, nullable=False)
    book_name: Mapped[str] = mapped_column(String(512), nullable=False, default="", server_default="")
    platform_name: Mapped[str] = mapped_column(String(64), nullable=False, default="", server_default="")
    pitcher_ids: Mapped[list[int]] = mapped_column(ARRAY(Integer), nullable=False)
    all_stat_cost_trend: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    all_stat_total_cost_trend: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    all_gmv_trend: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    all_billing_gmv_0day_trend: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    all_billing_gmv_24h_trend: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    all_billing_gmv_3days_trend: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    all_income_trend: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    all_income_0day_trend: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    all_pay_amount_income_trend: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    all_micro_game_income_trend: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    new_project_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    all_show_cnt_trend: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0, server_default="0")
    all_click_cnt_trend: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0, server_default="0")


class ReportUniPitcherDramaDay(BaseModel):
    """全域投手短剧收益。一个投手、一部剧、一天一行。"""

    __tablename__ = "report_uni_pitcher_drama_day"
    __table_args__ = (
        UniqueConstraint(
            "stat_date",
            "pitcher_id",
            "series_id",
            name="uq_report_uni_pitcher_drama_day",
        ),
        Index("ix_report_uni_pitcher_drama_day_owner", "pitcher_id", "stat_date"),
        {"comment": "全域投手短剧收益日表。"},
    )

    stat_date: Mapped[date] = mapped_column(Date, nullable=False)
    pitcher_id: Mapped[int] = mapped_column(Integer, nullable=False)
    pitcher_name: Mapped[str] = mapped_column(String(64), nullable=False, default="", server_default="")
    series_id: Mapped[int] = mapped_column(Integer, nullable=False)
    book_name: Mapped[str] = mapped_column(String(512), nullable=False, default="", server_default="")
    platform_name: Mapped[str] = mapped_column(String(64), nullable=False, default="", server_default="")
    all_stat_cost_trend: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    all_stat_total_cost_trend: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    all_gmv_trend: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    all_billing_gmv_0day_trend: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    all_billing_gmv_24h_trend: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    all_billing_gmv_3days_trend: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    all_income_trend: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    all_income_0day_trend: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    all_pay_amount_income_trend: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    all_micro_game_income_trend: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    new_project_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    all_show_cnt_trend: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0, server_default="0")
    all_click_cnt_trend: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0, server_default="0")


class ReportUniPitcherDay(BaseModel):
    """全域投手报表。一个投手一天一行。"""

    __tablename__ = "report_uni_pitcher_day"
    __table_args__ = (
        UniqueConstraint("stat_date", "pitcher_id", name="uq_report_uni_pitcher_day"),
        Index("ix_report_uni_pitcher_day_owner", "pitcher_id", "stat_date"),
        {"comment": "全域投手报表日表。"},
    )

    stat_date: Mapped[date] = mapped_column(Date, nullable=False)
    pitcher_id: Mapped[int] = mapped_column(Integer, nullable=False)
    pitcher_name: Mapped[str] = mapped_column(String(64), nullable=False, default="", server_default="")
    all_stat_cost_trend: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    all_stat_total_cost_trend: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    all_gmv_trend: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    all_billing_gmv_0day_trend: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    all_billing_gmv_24h_trend: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    all_billing_gmv_3days_trend: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    all_income_trend: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    all_income_0day_trend: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    all_pay_amount_income_trend: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    all_micro_game_income_trend: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    new_project_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    all_show_cnt_trend: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0, server_default="0")
    all_click_cnt_trend: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0, server_default="0")


class ReportUniGroupDay(BaseModel):
    """全域组报表。一个部门一天一行。"""

    __tablename__ = "report_uni_group_day"
    __table_args__ = (
        UniqueConstraint("stat_date", "department_id", name="uq_report_uni_group_day"),
        Index("ix_report_uni_group_day_dept", "department_id", "stat_date"),
        {"comment": "全域组报表日表。"},
    )

    stat_date: Mapped[date] = mapped_column(Date, nullable=False)
    department_id: Mapped[int] = mapped_column(Integer, nullable=False)
    department_name: Mapped[str] = mapped_column(String(128), nullable=False, default="", server_default="")
    all_stat_cost_trend: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    all_stat_total_cost_trend: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    all_gmv_trend: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    all_billing_gmv_0day_trend: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    all_billing_gmv_24h_trend: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    all_billing_gmv_3days_trend: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    all_income_trend: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    all_income_0day_trend: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    all_pay_amount_income_trend: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    all_micro_game_income_trend: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    new_project_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    all_show_cnt_trend: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0, server_default="0")
    all_click_cnt_trend: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0, server_default="0")


class ReportRoiConfig(BaseModel):
    """利润报表共用的 ROI 系数。日期重叠时，读取按创建时间最新的一条。"""

    __tablename__ = "report_roi_config"
    __table_args__ = (
        CheckConstraint("date_end >= date_start", name="ck_report_roi_config_range"),
        CheckConstraint("roi_rate >= 0", name="ck_report_roi_config_rate"),
        Index("ix_report_roi_config_range", "date_start", "date_end"),
        {"comment": "利润 ROI 系数。没覆盖到的统计日按 1.00。"},
    )

    date_start: Mapped[date] = mapped_column(Date, nullable=False, comment="生效起，含当天")
    date_end: Mapped[date] = mapped_column(Date, nullable=False, comment="生效止，含当天")
    roi_rate: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False, comment="ROI 系数，两位小数")


class ReportProfitDay(BaseModel):
    """利润日切片。一个统计日、投放范围、收费模式、剧类型、平台、部门、投手一行。"""

    __tablename__ = "report_profit_day"
    __table_args__ = (
        UniqueConstraint(
            "stat_date",
            "scope",
            "charge_mode",
            "drama_type",
            "platform",
            "department_id",
            "pitcher_id",
            name="uq_report_profit_day",
        ),
        CheckConstraint("scope IN ('standard', 'uni')", name="ck_report_profit_day_scope"),
        CheckConstraint("platform IN ('tomato', 'ouxi')", name="ck_report_profit_day_platform"),
        Index("ix_report_profit_day_date", "stat_date"),
        {"comment": "利润日表。盈亏按 ROI 配置在读取时算，不落库。"},
    )

    stat_date: Mapped[date] = mapped_column(Date, nullable=False)
    scope: Mapped[str] = mapped_column(String(16), nullable=False, comment="standard 标准，uni 全域")
    charge_mode: Mapped[str] = mapped_column(
        String(8), nullable=False, default="", server_default="", comment="IAA、IAP，或空"
    )
    drama_type: Mapped[str] = mapped_column(String(16), nullable=False, default="", server_default="")
    platform: Mapped[str] = mapped_column(String(16), nullable=False, comment="tomato 番茄，ouxi 鸥溪")
    department_id: Mapped[int] = mapped_column(Integer, nullable=False, comment="投手部门。没有部门时为 0")
    department_name: Mapped[str] = mapped_column(String(128), nullable=False, default="", server_default="")
    pitcher_id: Mapped[int] = mapped_column(Integer, nullable=False)
    pitcher_name: Mapped[str] = mapped_column(String(64), nullable=False, default="", server_default="")
    stat_cost: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False, comment="消耗")
    recovery: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False, comment="回收，即 stat_pay_amount")


class ReportMaterialDay(BaseModel):
    """素材日切片。一个统计日、头条素材、广告、项目一行。"""

    __tablename__ = "report_material_day"
    __table_args__ = (
        UniqueConstraint(
            "stat_date",
            "ocean_material_id",
            "promotion_id",
            "project_id",
            name="uq_report_material_day",
        ),
        CheckConstraint("scope IN ('standard', 'uni')", name="ck_report_material_day_scope"),
        Index("ix_report_material_day_date", "stat_date"),
        Index("ix_report_material_day_uploader", "uploader_id", "stat_date"),
        Index("ix_report_material_day_series", "series_id", "stat_date"),
        {"comment": "素材日表。列表按页面再汇总，不在请求时扫小时明细。"},
    )

    stat_date: Mapped[date] = mapped_column(Date, nullable=False)
    ocean_material_id: Mapped[int] = mapped_column(BigInteger, nullable=False, comment="头条素材 id")
    promotion_id: Mapped[int] = mapped_column(BigInteger, nullable=False, comment="巨量广告 id")
    promotion_name: Mapped[str] = mapped_column(Text, nullable=False, default="", server_default="")
    project_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    project_name: Mapped[str] = mapped_column(Text, nullable=False, default="", server_default="")
    scope: Mapped[str] = mapped_column(String(16), nullable=False)
    is_nobid: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=text("false"), comment="标准投放且模板名含 NB 或 CBO"
    )
    charge_mode: Mapped[str] = mapped_column(String(8), nullable=False, default="", server_default="")
    series_id: Mapped[int] = mapped_column(Integer, nullable=False)
    book_name: Mapped[str] = mapped_column(String(512), nullable=False, default="", server_default="")
    estimate_publish_date: Mapped[date | None] = mapped_column(Date, nullable=True, comment="短剧预估可投日")
    video_id: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="素材库 material_videos.id")
    material_name: Mapped[str] = mapped_column(Text, nullable=False, default="", server_default="")
    material_type: Mapped[str] = mapped_column(String(32), nullable=False, default="", server_default="")
    ownership: Mapped[str] = mapped_column(String(16), nullable=False, default="", server_default="")
    file_url: Mapped[str] = mapped_column(String(1024), nullable=False, default="", server_default="")
    uploader_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    uploader_name: Mapped[str] = mapped_column(String(64), nullable=False, default="", server_default="")
    uploader_department_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    uploader_department_name: Mapped[str] = mapped_column(String(128), nullable=False, default="", server_default="")
    pitcher_id: Mapped[int] = mapped_column(Integer, nullable=False, comment="投放账户上的投手")
    pitcher_name: Mapped[str] = mapped_column(String(64), nullable=False, default="", server_default="")
    video_pitcher_ids: Mapped[list[int]] = mapped_column(ARRAY(Integer), nullable=False)
    video_pitcher_names: Mapped[list[str]] = mapped_column(ARRAY(Text), nullable=False)
    stat_cost: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    recovery: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    show_cnt: Mapped[int] = mapped_column(BigInteger, nullable=False)
    click_cnt: Mapped[int] = mapped_column(BigInteger, nullable=False)
    convert_cnt: Mapped[int] = mapped_column(BigInteger, nullable=False)


class ReportHomeField(BaseModel):
    """首页三个自选。一个用户、一个表面一行。漫剧 IAA/IAP 共用 surface=manhua。"""

    __tablename__ = "report_home_field"
    __table_args__ = (
        UniqueConstraint("user_id", "surface", name="uq_report_home_field_user_surface"),
        CheckConstraint(
            "surface IN ('manhua', 'uni_drama', 'uni_pitcher_drama', 'uni_pitcher', 'uni_group')",
            name="ck_report_home_field_surface",
        ),
        {"comment": "首页自选字段。GET 不写缺省。"},
    )

    user_id: Mapped[int] = mapped_column(Integer, nullable=False)
    surface: Mapped[str] = mapped_column(String(32), nullable=False)
    field_1: Mapped[str] = mapped_column(String(64), nullable=False)
    field_2: Mapped[str] = mapped_column(String(64), nullable=False)
    field_3: Mapped[str] = mapped_column(String(64), nullable=False)
