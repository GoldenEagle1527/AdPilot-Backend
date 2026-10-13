"""免费和付费漫剧端原生机器人。执行留在规则所属投手。"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Index, Integer, Numeric, String, text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import BaseModel

_TS = DateTime(timezone=True)


class StandardNativeRobotRule(BaseModel):
    """一条标准端原生机器人规则。免费用 IAA 模板，付费用 IAP 模板。"""

    __tablename__ = "standard_native_robot_rule"
    __table_args__ = (
        CheckConstraint("charge_mode IN ('IAA', 'IAP')", name="ck_std_native_robot_charge"),
        CheckConstraint(
            "rule_kind IN ('nb', 'drama', 'promotion_link')",
            name="ck_std_native_robot_kind",
        ),
        CheckConstraint(
            "schedule_kind IN ('hourly', 'period', 'daily', 'cycle')",
            name="ck_std_native_robot_schedule",
        ),
        CheckConstraint(
            "schedule_minute BETWEEN 0 AND 59",
            name="ck_std_native_robot_minute",
        ),
        CheckConstraint(
            "schedule_hour IS NULL OR schedule_hour BETWEEN 0 AND 23",
            name="ck_std_native_robot_hour",
        ),
        CheckConstraint(
            "schedule_end_hour IS NULL OR schedule_end_hour BETWEEN 0 AND 23",
            name="ck_std_native_robot_end_hour",
        ),
        CheckConstraint(
            "schedule_end_minute IS NULL OR schedule_end_minute BETWEEN 0 AND 59",
            name="ck_std_native_robot_end_minute",
        ),
        CheckConstraint(
            "delivery_hours IS NULL OR delivery_hours BETWEEN 1 AND 8760",
            name="ck_std_native_robot_delivery_hours",
        ),
        CheckConstraint(
            "bid_type IS NULL OR bid_type IN ('CUSTOM', 'NO_BID')",
            name="ck_std_native_robot_bid",
        ),
        CheckConstraint(
            "cycle_minutes IS NULL OR cycle_minutes BETWEEN 1 AND 1440",
            name="ck_std_native_robot_cycle",
        ),
        CheckConstraint("sort_order >= 0", name="ck_std_native_robot_sort"),
        CheckConstraint(
            "accounts_per_series BETWEEN 1 AND 20",
            name="ck_std_native_robot_accounts",
        ),
        CheckConstraint(
            "max_videos_per_series BETWEEN 1 AND 800",
            name="ck_std_native_robot_videos",
        ),
        Index(
            "ix_std_native_robot_pitcher",
            "pitcher_user_id",
            postgresql_where=text("is_deleted = 0"),
        ),
        {"comment": "标准端原生机器人。免费菜单 76，付费菜单 77。"},
    )

    name: Mapped[str] = mapped_column(String(128), nullable=False, comment="规则名称")
    charge_mode: Mapped[str] = mapped_column(String(8), nullable=False, comment="IAA 免费机器人、IAP 付费机器人")
    rule_kind: Mapped[str] = mapped_column(
        String(32), nullable=False, comment="nb、drama、promotion_link"
    )
    schedule_kind: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        comment="hourly/cycle 按间隔，period/daily 每天定点",
    )
    schedule_hour: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="每天开始或定点的小时")
    schedule_minute: Mapped[int] = mapped_column(Integer, nullable=False, comment="每天开始或定点的分钟")
    schedule_end_hour: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="每天结束小时。NB 起止时间")
    schedule_end_minute: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="每天结束分钟")
    delivery_hours: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="NB 投放时间，单位小时")
    bid_type: Mapped[str | None] = mapped_column(
        String(16), nullable=True, comment="NB 竞价策略 CUSTOM 稳定成本、NO_BID 最大转化"
    )
    cycle_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="NB 周期，单位分钟")
    sort_order: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default=text("0"), comment="排序，小的在前"
    )
    template_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("delivery_template.id", ondelete="RESTRICT"), nullable=False
    )
    pitcher_user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, comment="规则所属投手"
    )
    platform_id: Mapped[int | None] = mapped_column(
        Integer, nullable=True, comment="剧场。剧条件和推广链规则都用，存剧场应用 id"
    )
    accounts_per_series: Mapped[int] = mapped_column(
        Integer, nullable=False, default=3, server_default=text("3"), comment="每部剧新账户数，默认 3"
    )
    max_videos_per_series: Mapped[int] = mapped_column(
        Integer, nullable=False, default=200, server_default=text("200"), comment="每部剧视频上限，执行不超过 800"
    )
    stat_span: Mapped[str | None] = mapped_column(String(16), nullable=True, comment="today 或 yesterday")
    cost_min: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    cost_max: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    recovery_min: Mapped[Decimal | None] = mapped_column(Numeric(10, 4), nullable=True, comment="回收比值")
    recovery_max: Mapped[Decimal | None] = mapped_column(Numeric(10, 4), nullable=True, comment="回收比值")
    is_enabled: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default=text("true")
    )
    last_ran_at: Mapped[datetime | None] = mapped_column(_TS, nullable=True, comment="上次执行时间")
