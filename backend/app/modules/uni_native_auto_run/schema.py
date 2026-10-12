"""端原生自动化投放执行记录的查询和出参。没有公开的新增入参。"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

RuleType = Literal["promotion_link", "drama_condition"]


class RunQuery(BaseModel):
    """执行记录列表。登录即可看全部未删除记录。"""

    model_config = ConfigDict(extra="forbid")

    page: int = Field(1, ge=1, description="页码，从 1 起")
    page_size: int = Field(20, ge=1, le=100, description="每页条数，最大 100")
    rule_type: RuleType | None = Field(
        None, description="规则类型。promotion_link 按推广链接，drama_condition 按剧条件"
    )
    series_name: str | None = Field(None, description="短剧名称，模糊。命中本次跑到的任一剧名")
    rule_id: int | None = Field(None, ge=1, description="规则 id，精确。即 uni_robot_rule.id")
    rule_name: str | None = Field(None, description="规则名称，模糊")


class FailureQuery(BaseModel):
    """一条执行记录下的失败日志。"""

    model_config = ConfigDict(extra="forbid")

    page: int = Field(1, ge=1, description="页码，从 1 起")
    page_size: int = Field(20, ge=1, le=100, description="每页条数，最大 100")


class RunItem(BaseModel):
    """一条执行记录。时间为北京时间，精确到秒。"""

    id: str
    rule_id: str
    rule_name: str
    rule_type: str
    executed_at: str
    template_name: str
    status: str
    series_names: list[str]
    created_at: str
    updated_at: str


class FailureItem(BaseModel):
    """一条失败日志。"""

    id: str
    series_name: str
    reason: str
    created_at: str
