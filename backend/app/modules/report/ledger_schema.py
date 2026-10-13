"""利润报表和素材报表的入参、出参。"""

from __future__ import annotations

from datetime import date as Date
from decimal import Decimal
from typing import Literal, Sequence

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.modules.report.schema import ReportPage, _DateRange

ProfitMode = Literal["all", "standard", "iaa", "iap", "uni"]
ProfitSort = Literal["stat_cost", "recovery", "recovery_rate", "profit"]
PlatformCode = Literal["tomato", "ouxi"]
DramaType = Literal["真人剧", "漫剧"]
DeliveryFilter = Literal["all", "standard", "uni"]
DramaAge = Literal["新剧", "老剧"]


class _ProfitFilters(_DateRange):
    mode: ProfitMode = Field("all", description="all 全域+标准，standard 仅标准，iaa，iap，uni 仅全域")
    drama_type: DramaType | None = Field(None, description="剧类型。不传为全部")
    platform: PlatformCode | None = Field(None, description="tomato 番茄，ouxi 鸥溪。不传为全部")
    sort_by: ProfitSort = Field("stat_cost", description="排序字段")


class ProfitOverviewQuery(_ProfitFilters):
    department_id: int | None = Field(None, description="分组，即投手所在部门")


class ProfitDailyQuery(_ProfitFilters):
    pitcher_user_id: int | None = Field(None, description="投手。非负责人和非运营管理员时忽略，只看自己")


class ProfitPitcherQuery(_ProfitFilters):
    """投手利润。部门范围同组报表。"""


class ProfitGroupQuery(_ProfitFilters):
    """组利润。"""


class ProfitGroupPitcherQuery(_ProfitFilters):
    department_id: int = Field(description="点开的部门")


class RoiWrite(BaseModel):
    model_config = ConfigDict(extra="forbid")

    date_start: Date
    date_end: Date
    roi_rate: Decimal = Field(ge=0, le=Decimal("9999.99"), description="ROI 系数，最多两位小数")

    @field_validator("roi_rate")
    @classmethod
    def two_places(cls, value: Decimal) -> Decimal:
        exponent = value.as_tuple().exponent
        if isinstance(exponent, int) and exponent < -2:
            raise ValueError("ROI系数最多两位小数")
        return value

    @model_validator(mode="after")
    def check_dates(self) -> RoiWrite:
        if self.date_start > self.date_end:
            raise ValueError("日期段起不能晚于止")
        return self


class RoiQuery(BaseModel):
    model_config = ConfigDict(extra="forbid")

    page: int = Field(1, ge=1)
    page_size: int = Field(20, ge=1, le=100)


class ProfitMetrics(BaseModel):
    stat_cost: float = Field(description="消耗")
    recovery: float = Field(description="回收，stat_pay_amount")
    recovery_rate: float = Field(description="回收 / 消耗。合计行同样用合计回收除合计消耗")
    profit: float = Field(description="回收×0.95 − 消耗×当天 ROI 系数，跨天先按天算再相加")


class ProfitDateItem(ProfitMetrics):
    stat_date: str


class ProfitDepartmentItem(ProfitMetrics):
    department_id: int
    department_name: str


class ProfitPlatformItem(ProfitMetrics):
    platform: str
    platform_name: str


class ProfitPitcherItem(ProfitMetrics):
    pitcher_user_id: int
    pitcher_name: str


class RoiItem(BaseModel):
    id: int
    date_start: str
    date_end: str
    roi_rate: float
    created_date: str


class RoiPage(BaseModel):
    items: Sequence[RoiItem] = Field(serialization_alias="list", validation_alias="list")
    total: int
    page: int
    page_size: int


class DeletedRoi(BaseModel):
    id: int
    deleted: bool


class MaterialSpendQuery(_DateRange):
    pitcher_user_id: int | None = Field(None, description="投手。匹配视频上分配的投手，或投放账户上的投手")
    uploader_id: int | None = Field(None, description="上传者")
    sort_by: Literal["stat_cost"] = "stat_cost"


class MaterialDetailQuery(_DateRange):
    video_id: int | None = Field(None, description="素材库 id。与头条素材 id 二选一")
    ocean_material_id: int | None = Field(None, description="头条素材 id")
    delivery: DeliveryFilter = Field("all", description="标准广告、全域广告或全部")
    sort_by: Literal["stat_cost", "show_cnt", "click_cnt", "convert_cnt", "ctr", "cpc", "cpm", "conversion_rate", "conversion_cost"] = "stat_cost"

    @model_validator(mode="after")
    def one_material(self) -> MaterialDetailQuery:
        if (self.video_id is None) == (self.ocean_material_id is None):
            raise ValueError("数据详情要指定素材库 id 或头条素材 id 里的一个")
        return self


class EditorSpendQuery(_DateRange):
    uploader_id: int | None = Field(None, description="素材手，即视频上传人")
    department_id: int | None = Field(None, description="素材手所在部门")
    sort_by: Literal[
        "stat_cost",
        "cost_ex_nobid",
        "standard_non_nobid_cost",
        "standard_nobid_cost",
        "uni_gmv",
        "group_avg_roi",
    ] = "stat_cost"


class _DramaFilters(_DateRange):
    series_name: str | None = Field(None, max_length=128, description="短剧名称，模糊")
    drama_age: list[DramaAge] = Field(default_factory=list, description="新剧、老剧。新剧=预估可投日在查询区间内")
    sort_by: Literal["stat_cost", "material_count"] = "stat_cost"


class DramaSpendQuery(_DramaFilters):
    """短剧统计。"""


class DramaEditorQuery(_DramaFilters):
    uploader_id: int | None = Field(None, description="素材手。剪辑师或素材手账号忽略此参数，只看自己")


class VideoSpendQuery(_DramaFilters):
    uploader_id: int | None = Field(None, description="素材手。剪辑师或素材手账号忽略此参数，只看自己")


class NbDramaQuery(_DateRange):
    series_name: str | None = Field(None, max_length=128, description="短剧名称，模糊")
    sort_by: Literal["material_count", "estimate_publish_date"] = "material_count"

    @model_validator(mode="after")
    def dates_are_estimate(self) -> NbDramaQuery:
        """日期筛的是预估可投日，不是消耗日。校验仍用父类的起止。"""
        return self


class EditorStatQuery(_DateRange):
    uploader_id: int | None = Field(None, description="素材手。剪辑师或素材手账号忽略此参数，只看自己")
    department_id: int | None = Field(None, description="素材手所在部门，与素材手级联")
    sort_by: Literal["new_drama_count", "drama_count", "material_count", "stat_cost"] = "stat_cost"


class MaterialSpendItem(BaseModel):
    stat_date: str
    video_id: int | None
    ocean_material_id: int
    material_name: str
    file_url: str = Field(description="视频地址，封面取第一帧由前端处理")
    series_id: int
    book_name: str
    material_type: str
    material_type_name: str
    ownership: str
    ownership_name: str
    uploader_id: int | None
    uploader_name: str
    pitcher_names: str
    stat_cost: float


class CostSummary(BaseModel):
    stat_cost: float


class MaterialDetailItem(BaseModel):
    promotion_id: int = Field(description="广告 id，页上的创意")
    promotion_name: str = Field(description="广告名称，页上的广告主")
    project_id: int = Field(description="项目 id，页上的计划")
    ocean_material_id: int = Field(description="头条素材 id")
    pitcher_name: str
    stat_cost: float
    show_cnt: int
    click_cnt: int
    ctr: float = Field(description="点击率，百分数，点击/展示×100")
    cpc: float = Field(description="平均点击单价，消耗/点击")
    cpm: float = Field(description="平均千次展示费用，消耗/展示×1000")
    convert_cnt: int
    conversion_rate: float = Field(description="转化率，百分数，转化/点击×100")
    conversion_cost: float = Field(description="平均转化成本，消耗/转化")


class EditorSpendItem(BaseModel):
    stat_date: str
    uploader_id: int
    uploader_name: str
    cost_ex_nobid: float = Field(description="总消耗 − 标准 nobid 消耗")
    standard_non_nobid_cost: float
    standard_nobid_cost: float
    uni_gmv: float = Field(description="全域投放的回收金额。时间跨度跟查询走")
    group_avg_roi: float | None = Field(description="登录人所在部门全部素材手在查询区间的回收/消耗。汇总行为空")
    stat_cost: float


class EditorSpendSummary(BaseModel):
    cost_ex_nobid: float
    standard_non_nobid_cost: float
    standard_nobid_cost: float
    uni_gmv: float
    group_avg_roi: float | None = None
    stat_cost: float


class DramaSpendItem(BaseModel):
    series_id: int
    book_name: str
    material_count: int = Field(description="视频库里这部剧的素材数")
    stat_cost: float


class CountCostSummary(BaseModel):
    material_count: int
    stat_cost: float


class DramaEditorItem(DramaSpendItem):
    uploader_id: int
    uploader_name: str


class VideoSpendItem(BaseModel):
    video_id: int | None
    ocean_material_id: int
    file_url: str
    series_id: int
    book_name: str
    uploader_id: int | None
    uploader_name: str
    material_name: str
    stat_cost: float


class NbDramaItem(BaseModel):
    series_id: int
    book_name: str
    estimate_publish_date: str
    material_count: int = Field(description="这部剧在模板名含 NB 或 CBO 的计划里用到的素材数，可以为 0")


class CountSummary(BaseModel):
    material_count: int


class EditorStatItem(BaseModel):
    stat_date: str
    uploader_id: int
    uploader_name: str
    new_drama_count: int = Field(description="预估可投日等于这一天，且这一天有消耗的短剧数")
    drama_count: int = Field(description="这一天有消耗的短剧数")
    material_count: int = Field(description="这一天有消耗的素材数")
    stat_cost: float


class EditorStatSummary(BaseModel):
    new_drama_count: int
    drama_count: int
    material_count: int
    stat_cost: float


ProfitDatePage = ReportPage[ProfitDateItem, ProfitMetrics]
ProfitDepartmentPage = ReportPage[ProfitDepartmentItem, ProfitMetrics]
ProfitPlatformPage = ReportPage[ProfitPlatformItem, ProfitMetrics]
ProfitPitcherPage = ReportPage[ProfitPitcherItem, ProfitMetrics]
MaterialSpendPage = ReportPage[MaterialSpendItem, CostSummary]
MaterialDetailPage = ReportPage[MaterialDetailItem, CostSummary]
EditorSpendPage = ReportPage[EditorSpendItem, EditorSpendSummary]
DramaSpendPage = ReportPage[DramaSpendItem, CountCostSummary]
DramaEditorPage = ReportPage[DramaEditorItem, CountCostSummary]
VideoSpendPage = ReportPage[VideoSpendItem, CountCostSummary]
NbDramaPage = ReportPage[NbDramaItem, CountSummary]
EditorStatPage = ReportPage[EditorStatItem, EditorStatSummary]
