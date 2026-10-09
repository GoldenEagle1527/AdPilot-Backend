"""全域模板的入参和出参。多传字段一律 422。不收标准模板的 gender、age_bands。"""

from __future__ import annotations

from decimal import Decimal
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, field_validator

from app.modules.standard_delivery.model import ChargeMode, TitleSelectMode

NameText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=128)]
Money = Annotated[Decimal, Field(gt=0, le=Decimal("99999999.99"), max_digits=10, decimal_places=2)]
RoiCoefficient = Annotated[Decimal, Field(ge=0, le=Decimal("9999.999"), max_digits=7, decimal_places=3)]


class TemplateQuery(BaseModel):
    """全域模板列表。全员可见，不按投手拆模板。"""

    model_config = ConfigDict(extra="forbid")

    page: int = Field(1, ge=1, description="页码，从 1 起")
    page_size: int = Field(20, ge=1, le=100, description="每页条数，最大 100")
    name: str | None = Field(None, description="模板名称，模糊")
    subject_id: int | None = Field(None, description="投放主体 id")
    charge_mode: ChargeMode | None = Field(None, description="投放变现模式：IAA、IAP，不传为全部")


class TemplateWrite(BaseModel):
    """新增或整表保存。收费模式可以改。"""

    model_config = ConfigDict(extra="forbid")

    name: NameText = Field(description="模板名称，1–128 字")
    subject_id: int = Field(description="投放主体 id，须为全域投放且收费模式一致")
    charge_mode: ChargeMode = Field(description="投放变现模式：IAA 免费、IAP 付费")
    project_budget: Money = Field(description="项目预算，单位元")
    roi_coefficient: RoiCoefficient = Field(description="ROI 系数")
    aigc_dynamic_creative: bool = Field(description="AIGC 动态创意")
    title_select_mode: TitleSelectMode = Field(description="标题选择：manual 手动、auto 自动")


class DouyinRef(BaseModel):
    """模板上当前投手分配的一个全域抖音号。"""

    id: str
    aweme_id: str
    name: str


class TemplateItem(BaseModel):
    """一条全域模板。抖音号只含当前登录投手自己的分配。"""

    id: str
    name: str
    subject_id: str
    subject_name: str
    charge_mode: str
    project_budget: str
    roi_coefficient: str
    aigc_dynamic_creative: bool
    title_select_mode: str
    douyin_accounts: list[DouyinRef]
    created_at: str
    updated_at: str


class DouyinAssignWrite(BaseModel):
    """用这批号换掉当前投手在该模板上的分配。空数组表示清空。"""

    model_config = ConfigDict(extra="forbid")

    douyin_account_ids: list[int] = Field(max_length=100, description="全域抖音号 id，须已分配给当前投手")

    @field_validator("douyin_account_ids")
    @classmethod
    def reject_duplicates(cls, value: list[int]) -> list[int]:
        """同一次提交里不许重复。"""
        if len(value) != len(set(value)):
            raise ValueError("抖音号重复")
        return value


class DouyinAssignResult(BaseModel):
    """替换后，当前投手在这条模板上的抖音号。"""

    template_id: str
    douyin_accounts: list[DouyinRef]


class DeletedItem(BaseModel):
    """软删后的出参。"""

    id: str
    deleted: bool
