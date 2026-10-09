"""标准端原生机器人入参。"""

from __future__ import annotations

from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class RobotWrite(BaseModel):
    """新增一条免费或付费端原生机器人规则。"""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=128)
    rule_kind: Literal["nb", "drama", "promotion_link"]
    schedule_kind: Literal["hourly", "period"]
    schedule_hour: int | None = Field(None, ge=0, le=23)
    schedule_minute: int = Field(0, ge=0, le=59)
    template_id: int
    platform_id: int | None = None
    accounts_per_series: int = Field(3, ge=1, le=20)
    max_videos_per_series: int = Field(200, ge=1, le=800)
    stat_span: Literal["today", "yesterday"] | None = None
    cost_min: Decimal | None = None
    cost_max: Decimal | None = None
    recovery_min: Decimal | None = None
    recovery_max: Decimal | None = None
    is_enabled: bool = True


class RobotItem(BaseModel):
    """一条已保存的机器人规则。"""

    id: str
    name: str
    charge_mode: str
    rule_kind: str
    schedule_kind: str
    template_id: str
    pitcher_user_id: str
    is_enabled: bool
