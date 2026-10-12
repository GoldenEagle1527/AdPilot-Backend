"""标准端原生机器人入参和出参。多传字段一律 422。"""

from __future__ import annotations

from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class RobotWrite(BaseModel):
    """新增或整表保存一条免费或付费端原生机器人规则。"""

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


class RobotQuery(BaseModel):
    """机器人列表。名称和开关都不传就是当前投手在该菜单下的全部。"""

    model_config = ConfigDict(extra="forbid")

    page: int = Field(1, ge=1, description="页码，从 1 起")
    page_size: int = Field(20, ge=1, le=100, description="每页条数，最大 100")
    name: str | None = Field(None, description="规则名称，模糊，不传为全部")
    is_enabled: bool | None = Field(None, description="开关：true 开启、false 关闭，不传为全部")


class RobotSwitchWrite(BaseModel):
    """只改开关。不到点执行。"""

    model_config = ConfigDict(extra="forbid")

    is_enabled: bool = Field(description="开关：true 开启、false 关闭")


class RobotItem(BaseModel):
    """一条已保存的机器人规则。时间为北京时间，精确到秒。"""

    id: str
    name: str
    charge_mode: str
    rule_kind: str
    schedule_kind: str
    schedule_hour: int | None
    schedule_minute: int
    template_id: str
    pitcher_user_id: str
    platform_id: str | None
    accounts_per_series: int
    max_videos_per_series: int
    stat_span: str | None
    cost_min: str | None
    cost_max: str | None
    recovery_min: str | None
    recovery_max: str | None
    is_enabled: bool
    created_at: str
    updated_at: str


class RobotDeleted(BaseModel):
    """软删后的出参。"""

    id: str
    deleted: bool
