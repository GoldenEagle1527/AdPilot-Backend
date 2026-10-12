"""巨量市级编码上的城市分级。供标准投放模板的发展划分使用。"""

from __future__ import annotations

from sqlalchemy import CheckConstraint, Index, Integer, String, text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import BaseModel

_TIERS = "('一线', '新一线', '二线', '三线', '四线', '五线')"


class OceanCityTier(BaseModel):
    """一座城市的分级。ocean_code 是巨量行政信息里的市级 code。"""

    __tablename__ = "ocean_city_tier"
    __table_args__ = (
        CheckConstraint(f"tier IN {_TIERS}", name="ck_ocean_city_tier_tier"),
        Index(
            "uq_ocean_city_tier_code_alive",
            "ocean_code",
            unique=True,
            postgresql_where=text("is_deleted = 0"),
        ),
        {"comment": "城市分级。名单来自百度百科《中国城市新分级名单》，编码对齐巨量行政信息。"},
    )

    ocean_code: Mapped[str] = mapped_column(
        String(16), nullable=False, comment="巨量行政信息市级 code，创建项目时放入 audience.city"
    )
    name: Mapped[str] = mapped_column(String(64), nullable=False, comment="巨量返回的城市名")
    province_name: Mapped[str] = mapped_column(
        String(64), nullable=False, server_default="", comment="巨量返回的省级名称"
    )
    tier: Mapped[str] = mapped_column(String(8), nullable=False, comment="一线、新一线、二线、三线、四线、五线")
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, comment="百科名单里的顺序，从 0 起")
