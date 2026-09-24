"""视频素材表。"""

from __future__ import annotations

from enum import StrEnum

from sqlalchemy import ForeignKey, Index, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column, relationship

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
    """谁能看见。public 所有人可见；private 为创建者、共享表里的人，以及投手归属里的投手。"""
    # 公有
    PUBLIC = "public"
    # 私有
    PRIVATE = "private"


class MaterialVideoTag(BaseModel):
    """视频标签。同一短剧同一天的文案只存一行，多条素材共用。"""

    __tablename__ = "material_video_tags"

    name: Mapped[str] = mapped_column(
        String(600), nullable=False, unique=True, comment="标签文案，前端传入，如 甲剧0923"
    )
    videos: Mapped[list[MaterialVideo]] = relationship(back_populates="tag")


class MaterialVideo(BaseModel):
    """视频素材落库行。短剧只存 manhua_series 主键，剧名查询时回填；上传时间用公共列 created_date。"""

    __tablename__ = "material_videos"
    __table_args__ = (
        Index("ix_material_videos_series_uploader", "series_id", "uploader_id"),
        Index("ix_material_videos_ownership", "ownership"),
        Index("ix_material_videos_uploader", "uploader_id"),
        Index("ix_material_videos_tag_id", "tag_id"),
    )

    name: Mapped[str] = mapped_column(
        String(512), nullable=False, comment="素材名称，落库时已拼当日日期后缀，如 甲_20260923"
    )
    material_type: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        comment="素材类型，取 MaterialType：vertical_video 竖版视频、horizontal_video 横版视频、"
        "horizontal_image 大图横图、small_image 小图、vertical_image 大图竖图",
    )
    # ponytail: 文件地址用 PG 数组。按单个 url 查会扫数组；真要按 url 查再拆表。
    file_urls: Mapped[list[str]] = mapped_column(
        ARRAY(String(1024)), nullable=False, comment="素材文件 url 数组"
    )
    series_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("manhua_series.id"),
        nullable=False,
        comment="短剧，外键 manhua_series.id",
    )
    platform: Mapped[str] = mapped_column(
        String(16), nullable=False, comment="投放平台，取 Platform：tomato 番茄"
    )
    tag_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("material_video_tags.id"),
        nullable=False,
        comment="标签，外键 material_video_tags.id",
    )
    tag: Mapped[MaterialVideoTag] = relationship(back_populates="videos")
    ownership: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        comment="谁能看见，取 Ownership：public 所有人可见、private 仅创建者、被共享的人和已分配投手可见",
    )
    uploader_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id"),
        nullable=False,
        comment="上传者，外键 users.id",
    )
    shares: Mapped[list[MaterialVideoShare]] = relationship(back_populates="video")
    pitchers: Mapped[list[MaterialVideoPitcher]] = relationship(back_populates="video")


class MaterialVideoShare(BaseModel):
    """一条素材共享给一个能操作的人。取消共享只删这一行，他分过的投手还在。"""

    __tablename__ = "material_video_shares"
    __table_args__ = (
        UniqueConstraint("user_id", "video_id", name="uq_material_video_shares_user_video"),
        Index("ix_material_video_shares_video", "video_id"),
    )

    video_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("material_videos.id"),
        nullable=False,
        comment="素材，外键 material_videos.id",
    )
    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id"),
        nullable=False,
        comment="被共享的人，外键 users.id",
    )
    video: Mapped[MaterialVideo] = relationship(back_populates="shares")


class MaterialVideoPitcher(BaseModel):
    """某个操作人把素材分给一个投手。操作人被移出共享后，这些行保留。"""

    __tablename__ = "material_video_pitchers"
    __table_args__ = (
        UniqueConstraint(
            "video_id",
            "operator_id",
            "user_id",
            name="uq_material_video_pitchers_video_operator_user",
        ),
        Index("ix_material_video_pitchers_video", "video_id"),
    )

    video_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("material_videos.id"),
        nullable=False,
        comment="素材，外键 material_videos.id",
    )
    operator_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id"),
        nullable=False,
        comment="谁分的。上传者或当时的共享人，外键 users.id",
    )
    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id"),
        nullable=False,
        comment="投手，外键 users.id",
    )
    video: Mapped[MaterialVideo] = relationship(back_populates="pitchers")
