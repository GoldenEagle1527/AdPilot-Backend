"""素材标题表。"""

from __future__ import annotations

from enum import StrEnum

from sqlalchemy import ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import BaseModel


class TitleCategory(StrEnum):
    """标题分类。成员值即落库值，是 str 子类，可直接赋给 category 列。"""

    PAID = "paid"
    COMMON = "common"


class MaterialTitle(BaseModel):
    """素材标题落库行。上传时间用公共列 created_date，删除走公共软删列。"""

    __tablename__ = "material_titles"
    __table_args__ = (Index("ix_material_titles_category_uploader", "category", "uploader_id"),)

    title: Mapped[str] = mapped_column(String(512), nullable=False, comment="标题名称")
    category: Mapped[str] = mapped_column(
        String(16), nullable=False, comment="标题分类，取 TitleCategory：paid 付费标题、common 通用标题"
    )
    uploader_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id"),
        nullable=False,
        comment="上传者，外键 users.id",
    )
