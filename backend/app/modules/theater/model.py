"""三方剧场平台表、应用表，以及番茄推广链同步任务和推广链表。"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import BaseModel


class TheaterType(StrEnum):
    """剧场类型。新增本轮只开放端原生。"""

    # 小程序
    MINI_PROGRAM = "mini_program"
    # 端原生
    NATIVE = "native"


class DeliveryMode(StrEnum):
    """投放模式。一个应用只选一种。"""

    IAA = "IAA"
    IAP = "IAP"


class TheaterStyle(StrEnum):
    """剧场风格。"""

    # 真人剧
    LIVE_ACTION = "live_action"
    # 漫剧
    MANHUA = "manhua"


class TheaterPlatform(BaseModel):
    """三方剧场平台。不开放新建，只有番茄（id=1）和鸥溪（id=22）两条固定数据；创建/更新时间用公共列。"""

    # ponytail: 主键即业务平台 id，灌数据时显式写 1 和 22，自增序列没跟着动。
    # 将来开放新建平台，先 setval 把序列拨到 MAX(id)，否则会撞主键。

    __tablename__ = "theater_platforms"
    __table_args__ = ({"comment": "三方剧场平台。不开放新建，只有番茄（id=1）和鸥溪（id=22）。"},)

    name: Mapped[str] = mapped_column(String(32), nullable=False, unique=True, comment="平台名称，如 番茄、鸥溪")
    code: Mapped[str] = mapped_column(
        String(16), nullable=False, unique=True, comment="平台码，番茄 1011、鸥溪 4504"
    )
    sort_order: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0", comment="排序，升序"
    )
    is_enabled: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default=text("true"), comment="启用状态：true 启用、false 禁用"
    )
    supports_mini_program: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default=text("false"),
        comment="是否支持小程序，勾选后选小程序的页面才能用这个平台",
    )
    supports_native: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default=text("true"),
        comment="是否支持端原生，勾选后选端原生的页面才能用这个平台",
    )


class TheaterApp(BaseModel):
    """三方剧场应用。创建投放广告时从有效的应用里选；创建/更新时间用公共列。"""

    __tablename__ = "theater_apps"
    __table_args__ = (
        Index(
            "uq_theater_apps_platform_name",
            "platform_id",
            "name",
            unique=True,
            postgresql_where=text("is_deleted = 0"),
        ),
        {"comment": "三方剧场应用。创建投放广告时从有效的应用里选。"},
    )

    platform_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("theater_platforms.id"),
        nullable=False,
        comment="平台，外键 theater_platforms.id",
    )
    name: Mapped[str] = mapped_column(String(128), nullable=False, comment="剧场名称，同平台未删除的不重名")
    theater_type: Mapped[str] = mapped_column(
        String(16), nullable=False, comment="剧场类型，取 TheaterType：mini_program 小程序、native 端原生"
    )
    delivery_mode: Mapped[str] = mapped_column(
        String(8), nullable=False, comment="投放模式，取 DeliveryMode：IAA、IAP，单选"
    )
    style: Mapped[str] = mapped_column(
        String(16), nullable=False, comment="剧场风格，取 TheaterStyle：live_action 真人剧、manhua 漫剧"
    )
    ad_source: Mapped[str] = mapped_column(
        String(64), nullable=False, comment="广告来源名称，人工填写，巨量审核广告时使用"
    )
    is_valid: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default=text("true"), comment="状态：true 有效、false 无效"
    )


class PromotionTaskStatus(StrEnum):
    """推广链同步任务状态。爬虫即调常读获取推广链接列表-v2 接口。"""

    # 初始状态：已建，没到执行时间
    PENDING = "pending"
    # 需要爬虫：已到执行时间，排队等调接口
    QUEUED = "queued"
    # 爬虫处理中：正在调接口，含重试
    RUNNING = "running"
    SUCCESS = "success"
    # 重试用完仍失败，或常读没有符合的推广链
    FAILED = "failed"


class PromotionTaskSource(StrEnum):
    """任务来源。"""

    # 到预估可投时间自动建
    AUTO = "auto"
    # 批量采集手动建
    MANUAL = "manual"


class PromotionLinkSource(StrEnum):
    """推广链来源。"""

    # 常读接口同步
    API = "api"
    # 投手人工新增
    MANUAL = "manual"


class TheaterPromotionTask(BaseModel):
    """番茄推广链同步任务，一次采集一行。剧名、付费类型（tab_text）、短剧类型查询时从 manhua_series 回填。"""

    __tablename__ = "theater_promotion_tasks"
    __table_args__ = (
        Index("ix_theater_promotion_tasks_status_execute", "status", "execute_at"),
        Index("ix_theater_promotion_tasks_series", "series_id"),
        CheckConstraint(
            "charge_filter IS NULL OR charge_filter IN ('all', 'IAA', 'IAP')",
            name="ck_theater_promotion_tasks_charge",
        ),
        {"comment": "番茄推广链同步任务。一次采集一行，到预估可投时间自动建或批量采集手动建。"},
    )

    series_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("manhua_series.id"), nullable=False, comment="短剧，外键 manhua_series.id，调接口用其 book_id"
    )
    collector_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=True, comment="采集人，外键 users.id；自动触发为空，展示为系统"
    )
    source: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        default=PromotionTaskSource.AUTO,
        server_default=PromotionTaskSource.AUTO.value,
        comment="来源，取 PromotionTaskSource：auto 自动、manual 批量采集",
    )
    status: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        default=PromotionTaskStatus.PENDING,
        server_default=PromotionTaskStatus.PENDING.value,
        comment="状态，取 PromotionTaskStatus：pending 初始、queued 需要爬虫、running 爬虫处理中、success 成功、failed 失败",
    )
    reason: Mapped[str] = mapped_column(
        String(1024), nullable=False, default="", server_default="", comment="原因，常读响应 message 或本地失败原因"
    )
    execute_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, comment="执行时间（北京），到点才调接口"
    )
    finished_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, comment="完成时间（北京），成功或最终失败时写"
    )
    retry_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0", comment="已重试次数，最多 5 次"
    )
    charge_filter: Mapped[str | None] = mapped_column(
        String(8),
        nullable=True,
        comment="手动批量采集的付费类型：all 全部、IAA 免费、IAP 付费。空表示自动任务，按短剧页签过滤",
    )


class TheaterPromotionLink(BaseModel):
    """端原生推广链，一条推广链一行。剧名查询时从 manhua_series 回填。"""

    __tablename__ = "theater_promotion_links"
    __table_args__ = (
        Index(
            "uq_theater_promotion_links_promotion_id",
            "promotion_id",
            unique=True,
            postgresql_where=text("promotion_id IS NOT NULL"),
        ),
        Index("ix_theater_promotion_links_series", "series_id"),
        Index("ix_theater_promotion_links_app", "theater_app_id"),
        Index("ix_theater_promotion_links_publish_time", "publish_time"),
        {"comment": "端原生推广链。一条推广链一行，常读接口同步或投手人工新增。"},
    )

    theater_app_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("theater_apps.id"), nullable=True, comment="剧场，外键 theater_apps.id；对应不上为空"
    )
    series_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("manhua_series.id"), nullable=False, comment="短剧，外键 manhua_series.id"
    )
    task_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("theater_promotion_tasks.id"),
        nullable=True,
        comment="来自哪次同步任务，外键 theater_promotion_tasks.id；人工新增为空",
    )
    source: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        default=PromotionLinkSource.API,
        server_default=PromotionLinkSource.API.value,
        comment="来源，取 PromotionLinkSource：api 接口同步、manual 人工新增",
    )
    promotion_id: Mapped[int | None] = mapped_column(
        BigInteger, nullable=True, comment="常读 promotion_info.promotion_id，同步去重键；人工新增为空"
    )
    promotion_url: Mapped[str] = mapped_column(
        String(2048), nullable=False, comment="推广链，常读 promotion_info.promotion_url"
    )
    recharge_template_name: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
        default="",
        server_default="",
        comment="出价面板，常读 delivery.recharge_template_name；人工新增为档位名 IAA/中额/小额/超小额/超超小额",
    )
    media_config_type: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0", comment="常读付费墙类型：2 付费短剧、3 免费短剧、0 未知"
    )
    publish_time: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, comment="首发时间（北京），常读 book_info.publish_time"
    )
    promotion_create_time: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, comment="推广链创建时间（北京），常读 promotion_info.create_time"
    )
    package_app_key: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
        default="",
        server_default="",
        comment="常读 package.app_key 原值，留着对应剧场",
    )
    is_enabled: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default=text("true"), comment="启用状态：true 启用、false 停用"
    )
