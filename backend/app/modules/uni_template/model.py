"""全域模板上的抖音号分配。模板行本身在 delivery_template，不另建一份模板表。"""

from __future__ import annotations

from sqlalchemy import ForeignKey, Index, Integer, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import BaseModel


class DeliveryTemplateDouyin(BaseModel):
    """一个投手把自己的全域抖音号挂到一条全域模板上。

    模板全员可见。分配只属于这个投手，不覆盖别人的号。
    """

    __tablename__ = "delivery_template_douyin"
    __table_args__ = (
        UniqueConstraint(
            "template_id",
            "user_id",
            "douyin_account_id",
            name="uq_delivery_template_douyin_user_account",
        ),
        Index("ix_delivery_template_douyin_user_template", "user_id", "template_id"),
        {"comment": "投手把自己的全域抖音号挂到全域模板。每人一份。"},
    )

    template_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("delivery_template.id", ondelete="CASCADE"),
        nullable=False,
        comment="全域模板",
    )
    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        comment="分配这些号的投手",
    )
    douyin_account_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("douyin_account.id", ondelete="CASCADE"),
        nullable=False,
        comment="全域抖音号",
    )
