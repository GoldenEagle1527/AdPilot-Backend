from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, Index, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import BaseModel


class ManhuaSeries(BaseModel):
    """常读短剧/漫剧落库行。按专辑 ID 和剧名查找，两列联合索引，允许重复。"""

    __tablename__ = "manhua_series"
    __table_args__ = (Index("ix_manhua_series_playlet_book", "playlet_id", "book_name"),)
    thumb_url: Mapped[str] = mapped_column(String(1024), nullable=False, default="", comment="封面 URL")
    book_id: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0, comment="常读 book_id")
    playlet_id: Mapped[int] = mapped_column(
        BigInteger, nullable=False, default=0, comment="常读 playlet_id，抖音专辑 ID"
    )
    book_name: Mapped[str] = mapped_column(String(512), nullable=False, default="", comment="短剧名称")
    episode_amount: Mapped[int] = mapped_column(Integer, nullable=False, default=0, comment="集数")
    gender: Mapped[int] = mapped_column(Integer, nullable=False, default=0, comment="常读性别码")
    category_text: Mapped[str] = mapped_column(
        String(512), nullable=False, default="", comment="常读题材，逗号分隔，如 玄幻脑洞,逆袭"
    )
    tab_text: Mapped[str] = mapped_column(
        String(128), nullable=False, default="", comment="由 single_price 判断：不收费 IAA，收费 IAP"
    )
    publish_status: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, comment="常读出参：1 未发布、2 已发布、3 已下架"
    )
    publish_time: Mapped[str] = mapped_column(
        String(64), nullable=False, default="", comment="常读发布时间原串（北京朴素时间）"
    )
    estimate_publish_time: Mapped[str] = mapped_column(
        String(64), nullable=False, default="", comment="常读预估可投时间原串"
    )
    permission_status: Mapped[int] = mapped_column(Integer, nullable=False, default=0, comment="常读权限状态")
    create_time: Mapped[str] = mapped_column(
        String(64), nullable=False, default="", comment="常读侧创建时间原串"
    )
    douyin_nick_name: Mapped[str] = mapped_column(String(256), nullable=False, default="", comment="抖音号昵称")
    single_price: Mapped[str] = mapped_column(String(64), nullable=False, default="", comment="常读单价原串")
    abstract: Mapped[str] = mapped_column(String(4000), nullable=False, default="", comment="简介")
    delivery_status: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, comment="是否可投")
    collected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), comment="本库采集时间（北京）"
    )
