"""账户管理 HTTP 的入参和出参。写接口 extra=forbid。"""

from __future__ import annotations

from decimal import Decimal
from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

DeliveryMode = Literal["standard", "uni"]
LibraryKind = Literal["novel", "video"]
LibraryRole = Literal["fallback", "standard"]


class _Forbid(BaseModel):
    model_config = ConfigDict(extra="forbid")


class AssignAdvertisersBody(_Forbid):
    """把若干广告主分给一个投手。"""

    advertiser_ids: list[int] = Field(min_length=1)
    pitcher_user_id: int


class RenameAdvertiserItem(_Forbid):
    """一个广告主的新本地展示名。"""

    advertiser_id: int
    name: str = Field(min_length=1, max_length=512)


class RenameAdvertisersBody(_Forbid):
    """批量改本地展示名。"""

    items: list[RenameAdvertiserItem] = Field(min_length=1)


class RenameAdvertiserRow(BaseModel):
    """改名后的一行。"""

    advertiser_id: int
    account_name: str


class RenameAdvertiserList(BaseModel):
    """改名结果。对外列表字段是 list，不是分页。"""

    items: list[RenameAdvertiserRow] = Field(serialization_alias="list", validation_alias="list")


class UnbindAdvertisersBody(_Forbid):
    """解绑广告主。"""

    advertiser_ids: list[int] = Field(min_length=1)


class ImportAdvertisersData(BaseModel):
    """整份导入都通过后的计数。"""

    action: Literal["assign", "unbind"]
    success_count: int


class SubjectBody(_Forbid):
    """创建或修改投放主体。不接收 actual_bid、arpu。"""

    name: str = Field(min_length=1, max_length=256)
    subject_no: int
    short_name: str | None = Field(None, max_length=128)
    delivery_mode: DeliveryMode
    theater_name: str = Field(min_length=1, max_length=256)
    theater_kind: str = Field(min_length=1, max_length=64)
    charge_mode: str = Field(min_length=1, max_length=16)
    min_bid: Decimal = Field(max_digits=18, decimal_places=2)
    max_bid: Decimal = Field(max_digits=18, decimal_places=2)
    roi_goal: Decimal | None = Field(None, max_digits=10, decimal_places=3)
    department_id: int | None = None
    material_account_id: int
    dual_bid: bool
    bid_panel: str | None = Field(None, max_length=255)

    @model_validator(mode="after")
    def _bid_range(self) -> Self:
        if self.min_bid > self.max_bid:
            raise ValueError("min_bid 不能大于 max_bid")
        return self


class SubjectQuery(_Forbid):
    """投放主体分页筛选。"""

    page: int = Field(1, ge=1)
    page_size: int = Field(20, ge=1, le=100)
    name: str | None = None
    subject_no: int | None = None
    delivery_mode: DeliveryMode | None = None
    theater_kind: str | None = None


class SubjectItem(BaseModel):
    """一条投放主体。不含 actual_bid、arpu。"""

    id: int
    name: str
    subject_no: int
    short_name: str | None
    delivery_mode: str
    theater_name: str
    theater_kind: str
    charge_mode: str
    min_bid: float
    max_bid: float
    roi_goal: float | None
    department_id: int | None
    material_account_id: int
    dual_bid: bool
    bid_panel: str | None


class DouyinQuery(_Forbid):
    """抖音号列表。标准模式不能带部门。"""

    delivery_mode: DeliveryMode
    aweme_id: str | None = None
    name: str | None = None
    department_id: int | None = None
    page: int = Field(1, ge=1)
    page_size: int = Field(20, ge=1, le=100)

    @model_validator(mode="after")
    def _standard_has_no_department(self) -> Self:
        if self.delivery_mode == "standard" and self.department_id is not None:
            raise ValueError("标准模式不能筛选部门")
        return self


class DouyinBody(_Forbid):
    """录入或修改抖音号。不接收投手列表。"""

    aweme_id: str = Field(min_length=1, max_length=64)
    name: str = Field(min_length=1, max_length=256)
    delivery_mode: DeliveryMode
    enabled: bool = True
    department_id: int | None = None
    owner_user_id: int | None = None

    @model_validator(mode="after")
    def _standard_has_no_owner(self) -> Self:
        if self.delivery_mode == "standard" and (
            self.department_id is not None or self.owner_user_id is not None
        ):
            raise ValueError("标准模式不能填写部门或负责人")
        return self


class DouyinUpdateBody(DouyinBody):
    """修改时启停必填，从开到关要查占用。"""

    enabled: bool


class DouyinItem(BaseModel):
    """一条抖音号。标准号的部门和投手恒空。"""

    id: int
    aweme_id: str
    name: str
    delivery_mode: str
    enabled: bool
    department_id: int | None
    owner_user_id: int | None
    pitcher_user_ids: list[int]


class DouyinEnabledBody(_Forbid):
    """直接改启停。"""

    enabled: bool


class DouyinEnabledData(BaseModel):
    """写入后的启停。"""

    id: int
    enabled: bool


class AssignPitchersBody(_Forbid):
    """覆盖投手集合。空数组表示不再挂投手。"""

    pitcher_user_ids: list[int]


class DouyinAssignData(BaseModel):
    """保存后的全域号投手。"""

    id: int
    pitcher_user_ids: list[int]


class DouyinReclaimData(BaseModel):
    """回收后部门与负责人为空，投手保留。"""

    id: int
    department_id: None
    owner_user_id: None
    pitcher_user_ids: list[int]


class ProductLibraryQuery(_Forbid):
    """商品库分页筛选。organization_id 是组织的巨量账户 id。"""

    page: int = Field(1, ge=1)
    page_size: int = Field(20, ge=1, le=100)
    name: str | None = None
    library_kind: LibraryKind | None = None
    organization_id: int | None = None


class ProductLibraryBody(_Forbid):
    """创建或修改商品库。不接收投手。"""

    name: str = Field(min_length=1, max_length=256)
    library_no: int
    library_kind: LibraryKind
    organization_id: int
    library_role: LibraryRole


class ProductLibraryItem(BaseModel):
    """一条商品库。organization_id 是巨量账户 id。"""

    id: int
    name: str
    library_no: int
    library_kind: str
    organization_id: int
    library_role: str
    uploaded_count: int
    pitcher_user_ids: list[int]


class ProductLibraryAssignData(BaseModel):
    """覆盖后的标准库投手。"""

    id: int
    pitcher_user_ids: list[int]


class SyncAdvertisersQuery(_Forbid):
    """手动同步。省略 oe_app_id 则同步全部有效应用。"""

    oe_app_id: int | None = None


class SyncAdvertisersData(BaseModel):
    """本次写入或更新的未删除广告主行数。"""

    advertiser_count: int
