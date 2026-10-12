"""全域漫剧机器人规则。

只保存规则本身。不创建巨量任务，也不在这里触发每天的时分。
模板 id、平台 id 仍不建外键。模板是否存在由目录端口查全域模板；剧场平台还没有来源。
"""

from __future__ import annotations

from decimal import Decimal
from enum import StrEnum

from sqlalchemy import Boolean, CheckConstraint, ForeignKey, Index, Integer, Numeric, String, text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import BaseModel


class RuleKind(StrEnum):
    """规则类型。"""

    # 按推广链接创建批量任务
    PROMOTION_LINK = "promotion_link"
    # 按剧条件创建批量任务
    DRAMA_CONDITION = "drama_condition"


class StatSpan(StrEnum):
    """剧条件的统计时间。只有当天和昨天。"""

    TODAY = "today"
    YESTERDAY = "yesterday"


class UniRobotRule(BaseModel):
    """一条全域漫剧机器人规则。两种类型共用这一张表，形状由检查约束分开。"""

    __tablename__ = "uni_robot_rule"
    __table_args__ = (
        CheckConstraint(
            "max_videos_per_series BETWEEN 1 AND 10000",
            name="ck_uni_robot_rule_videos",
        ),
        CheckConstraint("schedule_hour BETWEEN 0 AND 23", name="ck_uni_robot_rule_hour"),
        CheckConstraint("schedule_minute BETWEEN 0 AND 59", name="ck_uni_robot_rule_minute"),
        CheckConstraint(
            "("
            "rule_kind = 'promotion_link' "
            "AND stat_span IS NULL "
            "AND cost_min IS NULL AND cost_max IS NULL "
            "AND recovery_min IS NULL AND recovery_max IS NULL"
            ") OR ("
            "rule_kind = 'drama_condition' "
            "AND stat_span IN ('today', 'yesterday') "
            "AND cost_min IS NOT NULL AND cost_max IS NOT NULL "
            "AND cost_min >= 0 AND cost_min <= cost_max "
            "AND recovery_min IS NOT NULL AND recovery_max IS NOT NULL "
            "AND recovery_min >= 0 AND recovery_min <= recovery_max"
            ")",
            name="ck_uni_robot_rule_shape",
        ),
        Index(
            "uq_uni_robot_rule_kind_name_alive",
            "rule_kind",
            "name",
            unique=True,
            postgresql_where=text("is_deleted = 0"),
        ),
        Index(
            "ix_uni_robot_rule_kind_alive",
            "rule_kind",
            postgresql_where=text("is_deleted = 0"),
        ),
        {"comment": "全域漫剧机器人规则。只保存，不创建巨量任务。"},
    )

    rule_kind: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        comment="规则类型：promotion_link 按推广链接、drama_condition 按剧条件",
    )
    name: Mapped[str] = mapped_column(String(128), nullable=False, comment="规则名称")
    pitcher_user_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=True,
        comment="规则所属投手。执行时只用这个投手的号和账户",
    )
    template_id: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="全域批量模板 id。不建外键，保存时由目录端口确认",
    )
    platform_id: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="剧场平台 id。不建外键，保存时由目录端口确认",
    )
    max_videos_per_series: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=800,
        server_default=text("800"),
        comment="每部剧最大视频素材数，默认 800",
    )
    schedule_hour: Mapped[int] = mapped_column(
        Integer, nullable=False, comment="每天触发的小时，0–23"
    )
    schedule_minute: Mapped[int] = mapped_column(
        Integer, nullable=False, comment="每天触发的分钟，0–59"
    )
    is_enabled: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default=text("false"),
        comment="开关：true 开启、false 关闭",
    )
    stat_span: Mapped[str | None] = mapped_column(
        String(16),
        nullable=True,
        comment="统计时间：today 当天、yesterday 昨天。仅按剧条件，按推广链接必须为空",
    )
    cost_min: Mapped[Decimal | None] = mapped_column(
        Numeric(12, 2),
        nullable=True,
        comment="消耗下限，单位元。仅按剧条件，与上限成对",
    )
    cost_max: Mapped[Decimal | None] = mapped_column(
        Numeric(12, 2),
        nullable=True,
        comment="消耗上限，单位元。仅按剧条件",
    )
    recovery_min: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 4),
        nullable=True,
        comment="回收率下限，百分比数值，80 表示 80%。仅按剧条件，与上限成对",
    )
    recovery_max: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 4),
        nullable=True,
        comment="回收率上限，百分比数值。仅按剧条件",
    )
