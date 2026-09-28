"""三方剧场平台表与应用表。"""

from __future__ import annotations

from enum import StrEnum

from sqlalchemy import Boolean, ForeignKey, Index, Integer, String, text
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
