"""端原生自动化投放的一次执行记录。

页面不能手建。行由以后的漫剧机器人执行器调用 record_run 写入。
这里不跑机器人，也不调用巨量。
"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Integer, String, text
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import BaseModel

_TS = DateTime(timezone=True)


class RunRuleType(StrEnum):
    """规则类型。与 uni_robot_rule.rule_kind 同一套取值。"""

    # 按推广链接
    PROMOTION_LINK = "promotion_link"
    # 按剧条件
    DRAMA = "drama_condition"


class RunStatus(StrEnum):
    """一次执行的结果。执行器写入，本模块不推断。"""

    SUCCESS = "success"
    FAILED = "failed"
    PARTIAL = "partial"


class UniNativeAutoRun(BaseModel):
    """一条自动化投放执行记录。名称是执行当时的快照。"""

    __tablename__ = "uni_native_auto_run"
    __table_args__ = (
        CheckConstraint(
            "rule_type IN ('promotion_link', 'drama_condition')",
            name="ck_uni_native_auto_run_type",
        ),
        CheckConstraint(
            "status IN ('success', 'failed', 'partial')",
            name="ck_uni_native_auto_run_status",
        ),
        CheckConstraint("char_length(rule_name) >= 1", name="ck_uni_native_auto_run_rule_name"),
        CheckConstraint("char_length(template_name) >= 1", name="ck_uni_native_auto_run_template_name"),
        Index(
            "ix_uni_native_auto_run_rule_alive",
            "rule_id",
            postgresql_where=text("is_deleted = 0"),
        ),
        Index(
            "ix_uni_native_auto_run_type_alive",
            "rule_type",
            postgresql_where=text("is_deleted = 0"),
        ),
        Index(
            "ix_uni_native_auto_run_executed_alive",
            "executed_at",
            postgresql_where=text("is_deleted = 0"),
        ),
        {"comment": "漫剧全域端原生自动化投放的执行记录。不手建，不在启动时灌入。"},
    )

    rule_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("uni_robot_rule.id", ondelete="RESTRICT"),
        nullable=False,
        comment="uni_robot_rule.id",
    )
    rule_name: Mapped[str] = mapped_column(String(128), nullable=False, comment="执行当时的规则名称")
    rule_type: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        comment="promotion_link 按推广链接、drama_condition 按剧条件",
    )
    executed_at: Mapped[datetime] = mapped_column(_TS, nullable=False, comment="执行时间")
    template_name: Mapped[str] = mapped_column(String(128), nullable=False, comment="执行当时的模板名称")
    status: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        comment="success 成功、failed 失败、partial 部分失败",
    )
    series_names: Mapped[list[str]] = mapped_column(
        ARRAY(String(512)),
        nullable=False,
        default=list,
        server_default=text("ARRAY[]::varchar(512)[]"),
        comment="本次跑到的短剧名称",
    )


class UniNativeAutoRunFailure(BaseModel):
    """一条执行失败日志。挂在某一次执行记录上。"""

    __tablename__ = "uni_native_auto_run_failure"
    __table_args__ = (
        CheckConstraint("char_length(series_name) >= 1", name="ck_uni_native_auto_run_failure_series"),
        CheckConstraint("char_length(reason) >= 1", name="ck_uni_native_auto_run_failure_reason"),
        Index(
            "ix_uni_native_auto_run_failure_run",
            "run_id",
            "id",
            postgresql_where=text("is_deleted = 0"),
        ),
        {"comment": "端原生自动化投放执行失败日志。没有公开的新增接口。"},
    )

    run_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("uni_native_auto_run.id", ondelete="CASCADE"),
        nullable=False,
        comment="执行记录",
    )
    series_name: Mapped[str] = mapped_column(String(512), nullable=False, comment="失败的短剧名称")
    reason: Mapped[str] = mapped_column(String(2000), nullable=False, comment="失败原因")
