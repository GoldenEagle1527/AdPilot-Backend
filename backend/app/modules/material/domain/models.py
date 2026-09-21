from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, Identity, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base

_TS = DateTime(timezone=True)


class ManhuaSeries(Base):
    __tablename__ = "manhua_series"
    __table_args__ = (UniqueConstraint("playlet_id", "book_name", name="uq_manhua_series_playlet_book"),)

    id: Mapped[int] = mapped_column(Integer, Identity(), primary_key=True)
    thumb_url: Mapped[str] = mapped_column(String(1024), nullable=False, default="")
    book_id: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    playlet_id: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    book_name: Mapped[str] = mapped_column(String(512), nullable=False, default="")
    episode_amount: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    gender: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    category_text: Mapped[str] = mapped_column(String(128), nullable=False, default="")
    publish_status: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    publish_time: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    estimate_publish_time: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    permission_status: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    create_time: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    douyin_nick_name: Mapped[str] = mapped_column(String(256), nullable=False, default="")
    single_price: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    abstract: Mapped[str] = mapped_column(String(4000), nullable=False, default="")
    delivery_status: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    collected_at: Mapped[datetime] = mapped_column(_TS, nullable=False, server_default=func.now())
