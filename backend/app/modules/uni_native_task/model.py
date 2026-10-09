"""漫剧全域端原生投放任务。只在本系统落库，不上传素材，也不调巨量。"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from enum import StrEnum

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Integer, Numeric, String, text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import BaseModel

_TS = DateTime(timezone=True)


class NativeTaskStatus(StrEnum):
    """saved 已保存。running 是假客户端还在组报文（执行中）。done 是假客户端结束（完成），不是巨量真上传。"""

    SAVED = "saved"
    RUNNING = "running"
    DONE = "done"


class UniNativeTask(BaseModel):
    """一条端原生投放任务。预算和 ROI 从全域模板抄来，客户端可以改，以任务上的数为准。"""

    __tablename__ = "uni_native_task"
    __table_args__ = (
        CheckConstraint(
            "status IN ('saved', 'running', 'done')",
            name="ck_uni_native_task_status",
        ),
        CheckConstraint(
            "project_budget > 0 AND project_budget <= 99999999.99",
            name="ck_uni_native_task_budget",
        ),
        CheckConstraint(
            "roi_coefficient >= 0 AND roi_coefficient <= 9999.999",
            name="ck_uni_native_task_roi",
        ),
        Index(
            "ix_uni_native_task_pitcher_created",
            "pitcher_user_id",
            "created_date",
            postgresql_where=text("is_deleted = 0"),
        ),
        Index(
            "ix_uni_native_task_series",
            "series_id",
            postgresql_where=text("is_deleted = 0"),
        ),
        {"comment": "漫剧全域端原生投放任务。确认提交在假客户端执行中改为 running，结束后改为 done。"},
    )

    template_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("delivery_template.id", ondelete="RESTRICT"),
        nullable=False,
        comment="全域模板",
    )
    pitcher_user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        comment="创建任务的投手，列表只看自己的",
    )
    series_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("manhua_series.id", ondelete="RESTRICT"),
        nullable=False,
        comment="短剧 manhua_series.id。简称是剧名前两个字，不另存列",
    )
    project_budget: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False, comment="项目预算，单位元。从模板抄来，可被本次提交覆盖"
    )
    roi_coefficient: Mapped[Decimal] = mapped_column(
        Numeric(10, 3), nullable=False, comment="ROI 系数。从模板抄来，可被本次提交覆盖"
    )
    status: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        default=NativeTaskStatus.SAVED,
        server_default=text("'saved'"),
        comment="saved 已保存、running 执行中、done 完成。done 只表示假客户端结束",
    )
    executed_at: Mapped[datetime | None] = mapped_column(
        _TS, nullable=True, comment="假客户端结束的时间。未提交为空"
    )


class UniNativeTaskAccount(BaseModel):
    """任务上的一行：一个全域抖音号对应一个广告账户。"""

    __tablename__ = "uni_native_task_account"
    __table_args__ = (
        Index(
            "uq_uni_native_task_account_douyin",
            "task_id",
            "douyin_account_id",
            unique=True,
        ),
        Index(
            "uq_uni_native_task_account_advertiser",
            "task_id",
            "advertiser_account_id",
            unique=True,
        ),
        Index("ix_uni_native_task_account_task", "task_id", "sort_order"),
        {"comment": "抖音号与广告账户一一对应。至少一行，由应用层保证。"},
    )

    task_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("uni_native_task.id", ondelete="CASCADE"),
        nullable=False,
        comment="投放任务",
    )
    douyin_account_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("douyin_account.id", ondelete="RESTRICT"),
        nullable=False,
        comment="全域抖音号，须已分给当前投手",
    )
    advertiser_account_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("advertiser_account.id", ondelete="RESTRICT"),
        nullable=False,
        comment="广告主行。请求里用巨量广告主 id",
    )
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, comment="请求里的顺序，从 0 起")


class UniNativeTaskLink(BaseModel):
    """客户端传来的推广链文本。不查剧场表，也不写剧场行。"""

    __tablename__ = "uni_native_task_link"
    __table_args__ = (
        CheckConstraint("charge_mode IN ('IAA', 'IAP')", name="ck_uni_native_task_link_charge"),
        CheckConstraint("char_length(link_text) >= 1", name="ck_uni_native_task_link_text"),
        Index("ix_uni_native_task_link_task", "task_id", "sort_order"),
        {"comment": "IAA 或 IAP 推广链文本。没有剧场外键。"},
    )

    task_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("uni_native_task.id", ondelete="CASCADE"),
        nullable=False,
        comment="投放任务",
    )
    charge_mode: Mapped[str] = mapped_column(String(8), nullable=False, comment="IAA 免费、IAP 付费")
    link_text: Mapped[str] = mapped_column(String(2048), nullable=False, comment="客户端传入的推广链文本")
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, comment="请求里的顺序，从 0 起")


class UniNativeTaskVideo(BaseModel):
    """任务上的视频。素材表存在时才接受 id，本表不建素材外键。"""

    __tablename__ = "uni_native_task_video"
    __table_args__ = (
        Index("uq_uni_native_task_video_pair", "task_id", "material_video_id", unique=True),
        Index("ix_uni_native_task_video_task", "task_id", "sort_order"),
        {"comment": "视频素材主键。material_videos 不在本迁移里，有表才校验。"},
    )

    task_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("uni_native_task.id", ondelete="CASCADE"),
        nullable=False,
        comment="投放任务",
    )
    material_video_id: Mapped[int] = mapped_column(
        Integer, nullable=False, comment="material_videos.id，应用层在表存在时校验"
    )
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, comment="请求里的顺序，从 0 起")


class UniNativeTaskTitle(BaseModel):
    """从标题库选来的标题。只存主键，不在这里新建标题库行。"""

    __tablename__ = "uni_native_task_title"
    __table_args__ = (
        Index("uq_uni_native_task_title_pair", "task_id", "material_title_id", unique=True),
        Index("ix_uni_native_task_title_task", "task_id", "sort_order"),
        {"comment": "标题库主键。material_titles 不在本迁移里，有表才校验。"},
    )

    task_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("uni_native_task.id", ondelete="CASCADE"),
        nullable=False,
        comment="投放任务",
    )
    material_title_id: Mapped[int] = mapped_column(
        Integer, nullable=False, comment="material_titles.id，应用层在表存在时校验"
    )
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, comment="请求里的顺序，从 0 起")


class UniNativeTaskBatchTitle(BaseModel):
    """批量复制的临时标题。只留在任务上，不插入标题库。"""

    __tablename__ = "uni_native_task_batch_title"
    __table_args__ = (
        CheckConstraint("char_length(title) >= 1", name="ck_uni_native_task_batch_title_text"),
        Index("ix_uni_native_task_batch_title_task", "task_id", "sort_order"),
        {"comment": "任务内临时标题。不写入 material_titles。"},
    )

    task_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("uni_native_task.id", ondelete="CASCADE"),
        nullable=False,
        comment="投放任务",
    )
    title: Mapped[str] = mapped_column(String(512), nullable=False, comment="临时标题文本")
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, comment="请求里的顺序，从 0 起")
