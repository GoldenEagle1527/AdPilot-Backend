"""漫剧标准投放的入参和出参。多传字段一律 422。"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Annotated
from zoneinfo import ZoneInfo

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

from app.modules.standard_delivery.model import ChargeMode, OptimizeGoal, Placement

BEIJING = ZoneInfo("Asia/Shanghai")

NameText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=128)]
PanelText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=64)]
Money = Annotated[Decimal, Field(gt=0, le=Decimal("99999999.99"), max_digits=10, decimal_places=2)]
CostBound = Annotated[Decimal, Field(ge=0, le=Decimal("99999999.99"), max_digits=10, decimal_places=2)]
RoiBound = Annotated[Decimal, Field(ge=0, le=Decimal("9999"), max_digits=8, decimal_places=4)]


def _aware(value: datetime) -> datetime:
    """无时区按北京时间，有时区折到北京。"""
    if value.tzinfo is None:
        return value.replace(tzinfo=BEIJING)
    return value.astimezone(BEIJING)


def _unique_ids(values: list[int], label: str) -> list[int]:
    """拒绝重复 id，顺序保留。"""
    if len(values) != len(set(values)):
        raise ValueError(f"{label}重复")
    return values


def _pair(start: object, end: object, label: str, *, allow_equal: bool) -> None:
    """上下限必须成对，且下限不超过上限。"""
    if (start is None) ^ (end is None):
        raise ValueError(f"{label}须同时填写开始和结束")
    if start is None or end is None:
        return
    if allow_equal:
        if start > end:
            raise ValueError(f"{label}的开始不能晚于结束")
        return
    if start >= end:
        raise ValueError(f"{label}的结束须晚于开始")


class TemplateQuery(BaseModel):
    """模板列表。收费模式必填，免费和付费分两次查。"""

    model_config = ConfigDict(extra="forbid")

    page: int = Field(1, ge=1, description="页码，从 1 起")
    page_size: int = Field(20, ge=1, le=100, description="每页条数，最大 100")
    charge_mode: ChargeMode = Field(description="IAA 免费、IAP 付费")
    name: str | None = Field(None, description="模板名称，模糊")
    subject_id: int | None = Field(None, description="投放主体 id")


class TemplateWrite(BaseModel):
    """新增模板。收费模式创建后不可改。"""

    model_config = ConfigDict(extra="forbid")

    name: NameText = Field(description="模板名称，1–128 字")
    charge_mode: ChargeMode = Field(description="IAA 免费、IAP 付费")
    subject_id: int = Field(description="投放主体 id，须为标准投放且收费模式一致")
    bid_panels: list[PanelText] = Field(default_factory=list, max_length=20, description="出价面板，付费至少一条")
    ads_per_account: int = Field(ge=1, le=100, description="每账户广告条数，1–100")

    @model_validator(mode="after")
    def panels_match_charge(self) -> TemplateWrite:
        """付费必须选出价面板，重复的面板直接拒。"""
        if len(self.bid_panels) != len(set(self.bid_panels)):
            raise ValueError("出价面板重复")
        if self.charge_mode == ChargeMode.IAP and not self.bid_panels:
            raise ValueError("付费模板至少选一个出价面板")
        return self


class TemplateUpdate(BaseModel):
    """改模板。不收收费模式。"""

    model_config = ConfigDict(extra="forbid")

    name: NameText = Field(description="模板名称，1–128 字")
    subject_id: int = Field(description="投放主体 id")
    bid_panels: list[PanelText] = Field(default_factory=list, max_length=20, description="出价面板")
    ads_per_account: int = Field(ge=1, le=100, description="每账户广告条数，1–100")

    @model_validator(mode="after")
    def panels_unique(self) -> TemplateUpdate:
        """重复的面板直接拒。付费是否为空交给服务层看原收费模式。"""
        if len(self.bid_panels) != len(set(self.bid_panels)):
            raise ValueError("出价面板重复")
        return self


class TemplateItem(BaseModel):
    """一条模板。时间为北京时间，精确到秒。"""

    id: str
    name: str
    charge_mode: str
    subject_id: str
    subject_name: str
    bid_panels: list[str]
    ads_per_account: int
    created_at: str
    updated_at: str


class DraftQuery(BaseModel):
    """草稿列表。只查当前投手自己的，收费模式必填。"""

    model_config = ConfigDict(extra="forbid")

    page: int = Field(1, ge=1, description="页码，从 1 起")
    page_size: int = Field(20, ge=1, le=100, description="每页条数，最大 100")
    charge_mode: ChargeMode = Field(description="IAA 免费、IAP 付费")
    template_id: int | None = Field(None, description="模板 id")
    subject_id: int | None = Field(None, description="模板上的投放主体 id")
    series_id: int | None = Field(None, description="短剧 id")
    douyin_account_id: int | None = Field(None, description="抖音号 id")
    library_no: int | None = Field(None, description="商品库的巨量库 id")
    placement: Placement | None = Field(None, description="版位")
    optimize_goal: OptimizeGoal | None = Field(None, description="优化目标")
    scheduled: bool | None = Field(None, description="true 只看已预约，false 只看未预约")


class DraftWrite(BaseModel):
    """保存草稿。抖音号只有一个；账户、视频、标题是列表。"""

    model_config = ConfigDict(extra="forbid")

    template_id: int = Field(description="模板 id")
    schedule_start: datetime | None = Field(None, description="预约执行开始。与结束同时空或同时有值")
    schedule_end: datetime | None = Field(None, description="预约执行结束")
    advertiser_ids: list[int] = Field(min_length=1, max_length=100, description="巨量广告主 id，与账户列表的 account_id 相同")
    douyin_account_id: int = Field(description="一个已启用的标准抖音号 id。多个账户共用")
    series_id: int = Field(description="一部短剧的 manhua_series.id")
    video_ids: list[int] = Field(min_length=1, max_length=200, description="视频素材 id，须属于这部剧")
    title_ids: list[int] = Field(min_length=1, max_length=100, description="当前用户自己的标题 id")
    placement: Placement = Field(description="版位：aweme、aweme_feed、universal")
    project_budget: Money = Field(description="项目预算，单位元")
    ad_budget: Money = Field(description="广告预算，单位元")
    optimize_goal: OptimizeGoal = Field(description="优化目标。免费只能是激活，付费只能是付费")
    library_no: int = Field(description="商品库的巨量库 id，即 product_library.library_no")

    @model_validator(mode="after")
    def check_lists_and_schedule(self) -> DraftWrite:
        """预约成对，列表不重复。抖音号是单个整数，传数组会在类型上被拒。"""
        _unique_ids(self.advertiser_ids, "账户")
        _unique_ids(self.video_ids, "视频")
        _unique_ids(self.title_ids, "标题")
        if self.schedule_start is not None:
            self.schedule_start = _aware(self.schedule_start)
        if self.schedule_end is not None:
            self.schedule_end = _aware(self.schedule_end)
        _pair(self.schedule_start, self.schedule_end, "预约执行", allow_equal=False)
        return self


class AccountItem(BaseModel):
    """草稿里的一个广告账户。"""

    advertiser_account_id: str
    advertiser_id: int
    name: str


class VideoRef(BaseModel):
    """草稿里的一条视频。"""

    id: str
    name: str


class TitleRef(BaseModel):
    """草稿里的一条标题。"""

    id: str
    title: str


class DraftItem(BaseModel):
    """一条草稿。主体和每账户广告条数从模板带出。"""

    id: str
    charge_mode: str
    template_id: str
    template_name: str
    subject_id: str
    subject_name: str
    bid_panels: list[str]
    ads_per_account: int
    pitcher_user_id: str
    schedule_start: str | None
    schedule_end: str | None
    douyin_account_id: str
    aweme_id: str
    douyin_name: str
    series_id: str
    book_name: str
    accounts: list[AccountItem]
    videos: list[VideoRef]
    titles: list[TitleRef]
    placement: str
    project_budget: str
    ad_budget: str
    optimize_goal: str
    product_library_id: str
    library_no: int
    library_name: str
    created_at: str
    updated_at: str


class RuleQuery(BaseModel):
    """自动规则列表。只查当前投手自己的。"""

    model_config = ConfigDict(extra="forbid")

    page: int = Field(1, ge=1, description="页码，从 1 起")
    page_size: int = Field(20, ge=1, le=100, description="每页条数，最大 100")
    charge_mode: ChargeMode = Field(description="IAA 免费、IAP 付费")
    name: str | None = Field(None, description="规则名称，模糊")
    template_id: int | None = Field(None, description="模板 id")
    series_id: int | None = Field(None, description="选中了这部短剧")
    no_bid_only: bool | None = Field(None, description="是否只针对最大转化")
    scheduled: bool | None = Field(None, description="true 只看已预约，false 只看立即执行")


class RuleWrite(BaseModel):
    """保存自动规则。短剧可多选。不传的筛选范围表示不限。"""

    model_config = ConfigDict(extra="forbid")

    name: NameText = Field(description="规则名称，1–128 字")
    template_id: int = Field(description="批量模板 id")
    accounts_per_series: int = Field(3, ge=1, le=100, description="每部剧账户数，默认 3")
    max_videos_per_series: int = Field(200, ge=1, le=500, description="每部剧最大视频数，默认 200")
    schedule_start: datetime | None = Field(None, description="预约执行开始。空表示立即执行，本轮不跑")
    schedule_end: datetime | None = Field(None, description="预约执行结束")
    cost_min: CostBound | None = Field(None, description="短剧消耗下限，单位元")
    cost_max: CostBound | None = Field(None, description="短剧消耗上限，单位元")
    roi_min: RoiBound | None = Field(None, description="短剧回收率下限")
    roi_max: RoiBound | None = Field(None, description="短剧回收率上限")
    publish_start: date | None = Field(None, description="短剧上架日期下限")
    publish_end: date | None = Field(None, description="短剧上架日期上限")
    no_bid_only: bool = Field(False, description="真则只针对最大转化")
    series_ids: list[int] = Field(min_length=1, max_length=100, description="短剧 id，可多选")

    @model_validator(mode="after")
    def check_ranges(self) -> RuleWrite:
        """预约、消耗、回收、上架都要成对。短剧 id 不重复。"""
        _unique_ids(self.series_ids, "短剧")
        if self.schedule_start is not None:
            self.schedule_start = _aware(self.schedule_start)
        if self.schedule_end is not None:
            self.schedule_end = _aware(self.schedule_end)
        _pair(self.schedule_start, self.schedule_end, "预约执行", allow_equal=False)
        _pair(self.cost_min, self.cost_max, "短剧消耗", allow_equal=True)
        _pair(self.roi_min, self.roi_max, "短剧回收率", allow_equal=True)
        _pair(self.publish_start, self.publish_end, "短剧上架时间", allow_equal=True)
        return self


class SeriesRef(BaseModel):
    """规则里的一部短剧。"""

    id: str
    book_name: str


class RuleItem(BaseModel):
    """一条自动规则。"""

    id: str
    name: str
    charge_mode: str
    template_id: str
    template_name: str
    ads_per_account: int
    pitcher_user_id: str
    accounts_per_series: int
    max_videos_per_series: int
    schedule_start: str | None
    schedule_end: str | None
    cost_min: str | None
    cost_max: str | None
    roi_min: str | None
    roi_max: str | None
    publish_start: str | None
    publish_end: str | None
    no_bid_only: bool
    series: list[SeriesRef]
    created_at: str
    updated_at: str


class DeletedItem(BaseModel):
    """软删后的出参。"""

    id: str
    deleted: bool
