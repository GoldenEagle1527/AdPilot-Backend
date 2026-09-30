"""全域漫剧机器人规则的入参和出参。多传字段一律拒绝。"""

from __future__ import annotations

from decimal import Decimal
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

from app.modules.uni_robot.model import StatSpan

NameText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=128)]
CostBound = Annotated[Decimal, Field(ge=0, le=Decimal("99999999.99"), max_digits=10, decimal_places=2)]
RecoveryBound = Annotated[Decimal, Field(ge=0, le=Decimal("9999"), max_digits=8, decimal_places=4)]


class RuleClock(BaseModel):
    """两种规则共有的名称、目录 id、素材上限、每天时分和开关。"""

    model_config = ConfigDict(extra="forbid")

    name: NameText = Field(description="规则名称，去首尾空白，1–128 字")
    template_id: int = Field(ge=1, description="全域批量模板 id，不透明，由目录端口确认")
    platform_id: int = Field(ge=1, description="剧场平台 id，不透明，由目录端口确认")
    max_videos_per_series: int = Field(800, ge=1, le=10000, description="每部剧最大视频素材数，默认 800")
    schedule_hour: int = Field(ge=0, le=23, description="每天触发的小时，0–23")
    schedule_minute: int = Field(ge=0, le=59, description="每天触发的分钟，0–59")
    is_enabled: bool = Field(False, description="开关：true 开启、false 关闭")


class LinkRuleWrite(RuleClock):
    """按推广链接创建批量任务。没有统计时间、消耗区间、回收率区间。"""


class LinkRuleQuery(BaseModel):
    """按推广链接规则的列表。名称和开关都不传就是全部。"""

    model_config = ConfigDict(extra="forbid")

    page: int = Field(1, ge=1, description="页码，从 1 起")
    page_size: int = Field(20, ge=1, le=100, description="每页条数，最大 100")
    name: str | None = Field(None, description="规则名称，模糊，不传为全部")
    is_enabled: bool | None = Field(None, description="开关：true 开启、false 关闭，不传为全部")


class LinkSwitchWrite(BaseModel):
    """只改按推广链接规则的开关。"""

    model_config = ConfigDict(extra="forbid")

    is_enabled: bool = Field(description="开关：true 开启、false 关闭")


class LinkScheduleWrite(BaseModel):
    """只改按推广链接规则每天触发的时分。"""

    model_config = ConfigDict(extra="forbid")

    schedule_hour: int = Field(ge=0, le=23, description="每天触发的小时，0–23")
    schedule_minute: int = Field(ge=0, le=59, description="每天触发的分钟，0–59")


class LinkRuleItem(BaseModel):
    """一条按推广链接规则。不含剧条件列。"""

    id: str
    name: str
    template_id: str
    platform_id: str
    max_videos_per_series: int
    schedule_hour: int
    schedule_minute: int
    is_enabled: bool
    created_at: str
    updated_at: str


class LinkDeleted(BaseModel):
    """软删后的出参。"""

    id: str
    deleted: bool


class DramaRuleWrite(RuleClock):
    """按剧条件创建批量任务。统计时间只有当天或昨天，消耗和回收率都要给出区间。"""

    stat_span: StatSpan = Field(description="统计时间：today 当天、yesterday 昨天")
    cost_min: CostBound = Field(description="消耗下限，单位元")
    cost_max: CostBound = Field(description="消耗上限，单位元")
    recovery_min: RecoveryBound = Field(description="回收率下限，百分比数值，80 表示 80%")
    recovery_max: RecoveryBound = Field(description="回收率上限，百分比数值")

    @model_validator(mode="after")
    def ranges_in_order(self) -> DramaRuleWrite:
        """区间下限不能大于上限。两端相等可以。"""
        if self.cost_min > self.cost_max:
            raise ValueError("消耗区间的下限不能大于上限")
        if self.recovery_min > self.recovery_max:
            raise ValueError("回收率区间的下限不能大于上限")
        return self


class DramaRuleQuery(BaseModel):
    """按剧条件规则的列表。名称和开关都不传就是全部。"""

    model_config = ConfigDict(extra="forbid")

    page: int = Field(1, ge=1, description="页码，从 1 起")
    page_size: int = Field(20, ge=1, le=100, description="每页条数，最大 100")
    name: str | None = Field(None, description="规则名称，模糊，不传为全部")
    is_enabled: bool | None = Field(None, description="开关：true 开启、false 关闭，不传为全部")


class DramaSwitchWrite(BaseModel):
    """只改按剧条件规则的开关。"""

    model_config = ConfigDict(extra="forbid")

    is_enabled: bool = Field(description="开关：true 开启、false 关闭")


class DramaScheduleWrite(BaseModel):
    """只改按剧条件规则每天触发的时分。"""

    model_config = ConfigDict(extra="forbid")

    schedule_hour: int = Field(ge=0, le=23, description="每天触发的小时，0–23")
    schedule_minute: int = Field(ge=0, le=59, description="每天触发的分钟，0–59")


class DramaRuleItem(BaseModel):
    """一条按剧条件规则。"""

    id: str
    name: str
    template_id: str
    platform_id: str
    max_videos_per_series: int
    schedule_hour: int
    schedule_minute: int
    is_enabled: bool
    stat_span: str
    cost_min: str
    cost_max: str
    recovery_min: str
    recovery_max: str
    created_at: str
    updated_at: str


class DramaDeleted(BaseModel):
    """软删后的出参。"""

    id: str
    deleted: bool
