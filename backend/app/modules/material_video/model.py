"""视频素材表。"""

from __future__ import annotations

from enum import StrEnum

from sqlalchemy import Index, Integer, String
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import BaseModel


class MaterialType(StrEnum):
    """素材类型。成员值即落库值，是 str 子类，可直接赋给 material_type 列。"""

    # 竖版视频
    VERTICAL_VIDEO = "vertical_video"
    # 横版视频
    HORIZONTAL_VIDEO = "horizontal_video"
    # 横版图片
    HORIZONTAL_IMAGE = "horizontal_image"
    # 小图
    SMALL_IMAGE = "small_image"
    # 大图竖图
    VERTICAL_IMAGE = "vertical_image"


class Platform(StrEnum):
    """投放平台。本轮只有番茄。"""
    # 番茄
    TOMATO = "tomato"


class Ownership(StrEnum):
    """素材归属。public 公有、private 私有；本轮只落字段，不参与可见性过滤。"""
    # 公有
    PUBLIC = "public"
    # 私有
    PRIVATE = "private"


class MaterialVideo(BaseModel):
    """视频素材落库行。短剧只存 manhua_series 主键，剧名查询时回填；上传时间用公共列 created_date。"""

    __tablename__ = "material_videos"
    __table_args__ = (Index("ix_material_videos_series_uploader", "series_id", "uploader_id"),)

    name: Mapped[str] = mapped_column(
        String(512), nullable=False, comment="素材名称，落库时已拼当日日期后缀，如 甲_20260923"
    )
    material_type: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        comment="素材类型，取 MaterialType：vertical_video 竖版视频、horizontal_video 横版视频、"
        "horizontal_image 大图横图、small_image 小图、vertical_image 大图竖图",
    )
    # ponytail: 文件和投手用 PG 数组，不建关联表。上限是按投手筛选只能 = ANY 扫全表；
    # 真要按投手高频查再拆 material_video_pitchers 关联表或加 GIN 索引。
    file_urls: Mapped[list[str]] = mapped_column(
        ARRAY(String(1024)), nullable=False, comment="素材文件 url 数组"
    )
    series_id: Mapped[int] = mapped_column(
        Integer, nullable=False, comment="短剧，对应 manhua_series.id；不设外键，跨包只按值关联"
    )
    platform: Mapped[str] = mapped_column(
        String(16), nullable=False, comment="投放平台，取 Platform：tomato 番茄"
    )
    tag: Mapped[str] = mapped_column(
        String(600), nullable=False, comment="素材标签，落库时已拼成短剧名加当前月日，如 甲剧0923"
    )
    ownership: Mapped[str] = mapped_column(
        String(16), nullable=False, comment="归属，取 Ownership：public 公有、private 私有"
    )
    pitcher_ids: Mapped[list[int]] = mapped_column(
        ARRAY(Integer),
        nullable=False,
        comment="投手归属，对应 system_admin users.id，可多个；不设外键，跨包只按值关联",
    )
    uploader_id: Mapped[int] = mapped_column(
        Integer, nullable=False, comment="上传者，对应 system_admin users.id；不设外键，跨包只按值关联"
    )
