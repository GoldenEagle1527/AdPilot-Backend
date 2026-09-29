"""漫剧标准投放的本地草稿：模板、任务草稿、自动规则。

只存本系统要留的字段。不调用创建项目、创建单元，也不写巨量提交体。
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    text,
)
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import BaseModel

_TS = DateTime(timezone=True)


class ChargeMode(StrEnum):
    """免费 IAA、付费 IAP。和投放主体的收费模式用同一套值。"""

    IAA = "IAA"
    IAP = "IAP"


class Placement(StrEnum):
    """版位。抖音必选；头条是在抖音上再加；通投智能选单独一种。"""

    AWEME = "aweme"
    AWEME_FEED = "aweme_feed"
    UNIVERSAL = "universal"


class OptimizeGoal(StrEnum):
    """优化目标。免费只允许激活，付费只允许付费。"""

    ACTIVE = "AD_CONVERT_TYPE_ACTIVE"
    PAY = "AD_CONVERT_TYPE_PAY"


GOAL_BY_CHARGE = {
    ChargeMode.IAA: OptimizeGoal.ACTIVE,
    ChargeMode.IAP: OptimizeGoal.PAY,
}


class DeliveryTemplate(BaseModel):
    """投放模板。名称、主体、出价面板、每账户广告条数只留在本系统。"""

    __tablename__ = "delivery_template"
    __table_args__ = (
        CheckConstraint("charge_mode IN ('IAA', 'IAP')", name="ck_delivery_template_charge"),
        CheckConstraint(
            "ads_per_account BETWEEN 1 AND 100",
            name="ck_delivery_template_ads",
        ),
        Index(
            "uq_delivery_template_charge_name_alive",
            "charge_mode",
            "name",
            unique=True,
            postgresql_where=text("is_deleted = 0"),
        ),
        Index(
            "ix_delivery_template_charge_alive",
            "charge_mode",
            postgresql_where=text("is_deleted = 0"),
        ),
        {"comment": "漫剧标准投放模板。不存巨量创建项目的提交体。"},
    )

    name: Mapped[str] = mapped_column(String(128), nullable=False, comment="模板名称")
    charge_mode: Mapped[str] = mapped_column(
        String(8), nullable=False, comment="收费模式：IAA 免费、IAP 付费，创建后不可改"
    )
    subject_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("delivery_subject.id", ondelete="RESTRICT"),
        nullable=False,
        comment="投放主体，须为标准投放且收费模式一致",
    )
    bid_panels: Mapped[list[str]] = mapped_column(
        ARRAY(String(64)),
        nullable=False,
        default=list,
        server_default=text("ARRAY[]::varchar[]"),
        comment="出价面板，从主体的 bid_panel 里多选。免费可空",
    )
    ads_per_account: Mapped[int] = mapped_column(
        Integer, nullable=False, comment="每账户广告条数，1–100"
    )


class DeliveryTaskDraft(BaseModel):
    """投放任务草稿。一次只有一个抖音号，账户列表共用这一个号。

    不存推广链、产品主图、卖点、行动号召、事件资产、地域 code、巨量商品 id、巨量视频 id。
    """

    __tablename__ = "delivery_task_draft"
    __table_args__ = (
        CheckConstraint("charge_mode IN ('IAA', 'IAP')", name="ck_delivery_task_draft_charge"),
        CheckConstraint(
            "placement IN ('aweme', 'aweme_feed', 'universal')",
            name="ck_delivery_task_draft_placement",
        ),
        CheckConstraint(
            "(charge_mode = 'IAA' AND optimize_goal = 'AD_CONVERT_TYPE_ACTIVE') OR "
            "(charge_mode = 'IAP' AND optimize_goal = 'AD_CONVERT_TYPE_PAY')",
            name="ck_delivery_task_draft_goal",
        ),
        CheckConstraint("project_budget > 0 AND ad_budget > 0", name="ck_delivery_task_draft_budget"),
        CheckConstraint(
            "(schedule_start IS NULL AND schedule_end IS NULL) OR "
            "(schedule_start IS NOT NULL AND schedule_end IS NOT NULL AND schedule_start < schedule_end)",
            name="ck_delivery_task_draft_schedule",
        ),
        Index(
            "ix_delivery_task_draft_pitcher_charge",
            "pitcher_user_id",
            "charge_mode",
            postgresql_where=text("is_deleted = 0"),
        ),
        {"comment": "漫剧标准投放任务草稿。只给当前投手看自己的。确认提交不在本表。"},
    )

    template_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("delivery_template.id", ondelete="RESTRICT"),
        nullable=False,
        comment="投放模板",
    )
    charge_mode: Mapped[str] = mapped_column(
        String(8), nullable=False, comment="从模板抄来的收费模式，不随请求改"
    )
    pitcher_user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        comment="创建草稿的投手，列表只看自己的",
    )
    schedule_start: Mapped[datetime | None] = mapped_column(
        _TS, nullable=True, comment="预约执行开始。空表示未预约"
    )
    schedule_end: Mapped[datetime | None] = mapped_column(
        _TS, nullable=True, comment="预约执行结束。与开始同时空或同时有值"
    )
    douyin_account_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("douyin_account.id", ondelete="RESTRICT"),
        nullable=False,
        comment="唯一的标准抖音号。多个账户共用，不按投手过滤",
    )
    series_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("manhua_series.id", ondelete="RESTRICT"),
        nullable=False,
        comment="一部短剧",
    )
    placement: Mapped[str] = mapped_column(
        String(16), nullable=False, comment="版位：aweme 抖音、aweme_feed 抖音加头条、universal 通投智能选"
    )
    project_budget: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False, comment="项目预算，单位元"
    )
    ad_budget: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, comment="广告预算，单位元")
    optimize_goal: Mapped[str] = mapped_column(
        String(64), nullable=False, comment="优化目标。免费激活，付费付费"
    )
    product_library_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("product_library.id", ondelete="RESTRICT"),
        nullable=False,
        comment="商品库",
    )


class DeliveryTaskAccount(BaseModel):
    """草稿上的广告账户。整表替换，投手必须是这些户当前的投手。"""

    __tablename__ = "delivery_task_account"
    __table_args__ = (
        Index(
            "uq_delivery_task_account_pair",
            "task_id",
            "advertiser_account_id",
            unique=True,
        ),
        Index("ix_delivery_task_account_task", "task_id", "sort_order"),
        {"comment": "草稿账户。存的是广告主行，请求里用巨量广告主 id。"},
    )

    task_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("delivery_task_draft.id", ondelete="CASCADE"),
        nullable=False,
        comment="草稿",
    )
    advertiser_account_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("advertiser_account.id", ondelete="RESTRICT"),
        nullable=False,
        comment="广告主行",
    )
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, comment="请求里的顺序，从 0 起")


class DeliveryTaskVideo(BaseModel):
    """草稿上的视频素材。须属于所选短剧，且当前用户能看见。"""

    __tablename__ = "delivery_task_video"
    __table_args__ = (
        Index("uq_delivery_task_video_pair", "task_id", "material_video_id", unique=True),
        Index("ix_delivery_task_video_task", "task_id", "sort_order"),
        {"comment": "草稿视频。只存素材库主键，不存巨量 video_id。"},
    )

    task_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("delivery_task_draft.id", ondelete="CASCADE"),
        nullable=False,
        comment="草稿",
    )
    # 素材表不在现有迁移链里，本地库也可能还没有。这里只存主键，保存时再查 material_videos。
    material_video_id: Mapped[int] = mapped_column(
        Integer, nullable=False, comment="视频素材 material_videos.id，应用层校验"
    )
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, comment="请求里的顺序，从 0 起")


class DeliveryTaskTitle(BaseModel):
    """草稿上的标题。只收当前用户自己上传的标题。"""

    __tablename__ = "delivery_task_title"
    __table_args__ = (
        Index("uq_delivery_task_title_pair", "task_id", "material_title_id", unique=True),
        Index("ix_delivery_task_title_task", "task_id", "sort_order"),
        {"comment": "草稿标题。只存标题库主键。"},
    )

    task_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("delivery_task_draft.id", ondelete="CASCADE"),
        nullable=False,
        comment="草稿",
    )
    # 标题表同样不在现有迁移链里。保存时再查 material_titles。
    material_title_id: Mapped[int] = mapped_column(
        Integer, nullable=False, comment="标题 material_titles.id，应用层校验"
    )
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, comment="请求里的顺序，从 0 起")


class DeliveryAutoRule(BaseModel):
    """自动投放规则。保存和筛选在本系统，到点执行不在这一轮。

    剧场不落库：短剧表没有剧场外键，规则默认对着番茄漫剧库。
    """

    __tablename__ = "delivery_auto_rule"
    __table_args__ = (
        CheckConstraint("charge_mode IN ('IAA', 'IAP')", name="ck_delivery_auto_rule_charge"),
        CheckConstraint(
            "accounts_per_series BETWEEN 1 AND 100",
            name="ck_delivery_auto_rule_accounts",
        ),
        CheckConstraint(
            "max_videos_per_series BETWEEN 1 AND 500",
            name="ck_delivery_auto_rule_videos",
        ),
        CheckConstraint(
            "(schedule_start IS NULL AND schedule_end IS NULL) OR "
            "(schedule_start IS NOT NULL AND schedule_end IS NOT NULL AND schedule_start < schedule_end)",
            name="ck_delivery_auto_rule_schedule",
        ),
        CheckConstraint(
            "(cost_min IS NULL AND cost_max IS NULL) OR "
            "(cost_min IS NOT NULL AND cost_max IS NOT NULL AND cost_min >= 0 AND cost_min <= cost_max)",
            name="ck_delivery_auto_rule_cost",
        ),
        CheckConstraint(
            "(roi_min IS NULL AND roi_max IS NULL) OR "
            "(roi_min IS NOT NULL AND roi_max IS NOT NULL AND roi_min >= 0 AND roi_min <= roi_max)",
            name="ck_delivery_auto_rule_roi",
        ),
        CheckConstraint(
            "(publish_start IS NULL AND publish_end IS NULL) OR "
            "(publish_start IS NOT NULL AND publish_end IS NOT NULL AND publish_start <= publish_end)",
            name="ck_delivery_auto_rule_publish",
        ),
        Index(
            "uq_delivery_auto_rule_owner_name_alive",
            "pitcher_user_id",
            "charge_mode",
            "name",
            unique=True,
            postgresql_where=text("is_deleted = 0"),
        ),
        Index(
            "ix_delivery_auto_rule_pitcher_charge",
            "pitcher_user_id",
            "charge_mode",
            postgresql_where=text("is_deleted = 0"),
        ),
        {"comment": "漫剧标准投放自动规则。只保存筛选和模板，不调巨量。"},
    )

    name: Mapped[str] = mapped_column(String(128), nullable=False, comment="规则名称")
    charge_mode: Mapped[str] = mapped_column(
        String(8), nullable=False, comment="从模板抄来的收费模式"
    )
    template_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("delivery_template.id", ondelete="RESTRICT"),
        nullable=False,
        comment="批量模板",
    )
    pitcher_user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        comment="创建规则的投手，列表只看自己的",
    )
    accounts_per_series: Mapped[int] = mapped_column(
        Integer, nullable=False, default=3, server_default=text("3"), comment="每部剧使用的账户数，默认 3"
    )
    max_videos_per_series: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=200,
        server_default=text("200"),
        comment="每部剧最多取多少条视频，默认 200",
    )
    schedule_start: Mapped[datetime | None] = mapped_column(
        _TS, nullable=True, comment="预约执行开始。空表示立即执行，本轮仍不跑"
    )
    schedule_end: Mapped[datetime | None] = mapped_column(_TS, nullable=True, comment="预约执行结束")
    cost_min: Mapped[Decimal | None] = mapped_column(
        Numeric(12, 2), nullable=True, comment="短剧消耗下限，单位元。空表示不限"
    )
    cost_max: Mapped[Decimal | None] = mapped_column(
        Numeric(12, 2), nullable=True, comment="短剧消耗上限，单位元"
    )
    roi_min: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 4), nullable=True, comment="短剧回收率下限。空表示不限"
    )
    roi_max: Mapped[Decimal | None] = mapped_column(Numeric(10, 4), nullable=True, comment="短剧回收率上限")
    publish_start: Mapped[date | None] = mapped_column(
        Date, nullable=True, comment="短剧上架日期下限。筛 manhua_series.publish_time，不是报表时间"
    )
    publish_end: Mapped[date | None] = mapped_column(Date, nullable=True, comment="短剧上架日期上限")
    no_bid_only: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default=text("false"),
        comment="真则只针对最大转化。本轮只保存，不筛报表",
    )


class DeliveryAutoRuleSeries(BaseModel):
    """规则选中的短剧。可多选。"""

    __tablename__ = "delivery_auto_rule_series"
    __table_args__ = (
        Index("uq_delivery_auto_rule_series_pair", "rule_id", "series_id", unique=True),
        Index("ix_delivery_auto_rule_series_rule", "rule_id", "sort_order"),
        {"comment": "自动规则的短剧。剧场不另存。"},
    )

    rule_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("delivery_auto_rule.id", ondelete="CASCADE"),
        nullable=False,
        comment="规则",
    )
    series_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("manhua_series.id", ondelete="RESTRICT"),
        nullable=False,
        comment="短剧",
    )
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, comment="请求里的顺序，从 0 起")
