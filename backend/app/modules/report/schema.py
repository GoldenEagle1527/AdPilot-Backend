"""数据报表的入参和出参。口径见 Plan/product/数据报表/口径.md。"""

from __future__ import annotations

from datetime import date as Date
from typing import Generic, Literal, Sequence, TypeVar

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.core.times import beijing_now

T = TypeVar("T")
S = TypeVar("S")

MEDIA_OCEAN = "巨量"
DRAMA_TYPES = ("真人剧", "漫剧")
BID_TYPES = ("最大转化", "稳定成本")
DRAMA_AGES = ("新剧", "老剧")

MANHUA_SORT_FIELDS = (
    "stat_cost",
    "stat_pay_amount",
    "pay_amount_roi",
    "attribution_game_in_app_ltv_1day",
    "attribution_game_in_app_ltv_8days",
    "attribution_micro_game_0d_ltv",
    "attribution_micro_game_7d_ltv",
    "attribution_game_in_app_roi_1day",
    "attribution_game_in_app_roi_8days",
    "attribution_micro_game_0d_roi",
    "attribution_micro_game_7d_roi",
    "show_cnt",
    "cpm_platform",
    "click_cnt",
    "cpc_platform",
    "active",
    "active_cost",
    "convert_cnt",
    "conversion_cost",
    "ctr",
    "active_rate",
    "conversion_rate",
    "promotion_with_cost_count",
)
UNI_SORT_FIELDS = (
    "all_stat_cost_trend",
    "all_roi_24h_trend",
    "all_stat_total_cost_trend",
    "all_gmv_trend",
    "all_billing_gmv_0day_trend",
    "all_billing_gmv_24h_trend",
    "all_billing_gmv_3days_trend",
    "all_roi_trend",
    "all_roi_0day_trend",
    "all_roi_3days_trend",
    "all_income_trend",
    "all_income_0day_trend",
    "all_pay_amount_income_trend",
    "all_micro_game_income_trend",
    "new_project_count",
    "new_project_with_cost_count",
    "spending_project_count",
    "spending_advertiser_count",
    "new_drama_count",
)


def _today() -> Date:
    return beijing_now().date()


class _DateRange(BaseModel):
    model_config = ConfigDict(extra="forbid")

    page: int = Field(1, ge=1, description="页码，从 1 起")
    page_size: int = Field(20, ge=1, le=100, description="每页条数，最大 100")
    date_start: Date = Field(default_factory=_today, description="统计日期起，含当天，北京时间。默认今天")
    date_end: Date = Field(default_factory=_today, description="统计日期止，含当天，北京时间。默认今天")
    sort_order: Literal["asc", "desc"] = Field("desc", description="排序方向，默认倒序")

    @model_validator(mode="after")
    def check_dates(self) -> _DateRange:
        """起日不能晚于止日。"""
        if self.date_start > self.date_end:
            raise ValueError("日期段起不能晚于止")
        return self


class ManhuaQuery(_DateRange):
    """漫剧报表三层共用的筛选。哪一层收哪些筛选由 level 决定，多传按 422。"""

    charge_mode: Literal["IAP", "IAA"] = Field(description="IAP 付费（菜单 9）、IAA 免费（菜单 5）")
    series_id: list[int] = Field(default_factory=list, description="剧目 manhua_series.id，多选")
    series_name: str | None = Field(None, max_length=128, description="剧名，模糊")
    media: str = Field(MEDIA_OCEAN, max_length=16, description="投放媒体，默认巨量。本期只有巨量有数据")
    drama_type: list[Literal["真人剧", "漫剧"]] = Field(default_factory=list, description="剧目类型，多选")
    channel: list[str] = Field(default_factory=list, description="剧目渠道（剧场平台名），多选，如 番茄")
    bid_type: list[Literal["最大转化", "稳定成本"]] = Field(default_factory=list, description="投放类型，多选")
    panel: list[str] = Field(default_factory=list, description="面板，多选。只有付费")
    drama_age: list[Literal["新剧", "老剧"]] = Field(default_factory=list, description="新/老剧，多选")
    team: list[str] = Field(default_factory=list, description="团队，即投手所在部门名称，多选")
    pitcher: list[str] = Field(default_factory=list, description="优化师姓名，多选，精确匹配")
    sort_by: str = Field("stat_cost", description="排序字段，默认消耗")

    def check_level(self, level: str) -> None:
        """R1IAP 只收日期、投放类型、面板、新/老剧、团队；免费各层都没有面板。"""
        if self.sort_by not in MANHUA_SORT_FIELDS:
            raise ValueError("排序字段不支持")
        if self.charge_mode == "IAA" and self.panel:
            raise ValueError("免费报表没有面板筛选")
        if level == "drama" and self.charge_mode == "IAP":
            extra = [
                name
                for name in ("series_id", "series_name", "drama_type", "channel", "pitcher")
                if getattr(self, name)
            ]
            if extra or self.media != MEDIA_OCEAN:
                raise ValueError("付费剧目页只有日期、投放类型、面板、新/老剧、团队筛选")


class ManhuaDramaQuery(ManhuaQuery):
    @model_validator(mode="after")
    def check_page(self) -> ManhuaDramaQuery:
        self.check_level("drama")
        return self


class ManhuaProjectQuery(ManhuaQuery):
    @model_validator(mode="after")
    def check_page(self) -> ManhuaProjectQuery:
        self.check_level("project")
        return self


class ManhuaExportQuery(ManhuaQuery):
    level: Literal["drama", "project", "promotion"] = Field(description="导出哪一层：剧目、项目、计划")

    @model_validator(mode="after")
    def check_page(self) -> ManhuaExportQuery:
        self.check_level("drama" if self.level == "drama" else self.level)
        return self


class ManhuaTrendQuery(BaseModel):
    """漫剧趋势弹框：所选一天按小时的消耗和回收。"""

    model_config = ConfigDict(extra="forbid")

    charge_mode: Literal["IAP", "IAA"] = Field(description="IAP 付费（菜单 9）、IAA 免费（菜单 5）")
    grain: Literal["drama", "project", "promotion"] = Field(description="剧目、项目、计划")
    id: int = Field(description="剧目为 manhua_series.id，项目为 cdp_project_id，计划为 cdp_promotion_id")
    panel: str | None = Field(None, max_length=64, description="仅付费剧目：该行的面板。空串是没有面板的旧行")
    date: Date = Field(default_factory=_today, description="哪一天，北京时间，默认今天")

    @model_validator(mode="after")
    def check_panel(self) -> ManhuaTrendQuery:
        if self.panel is not None and not (self.grain == "drama" and self.charge_mode == "IAP"):
            raise ValueError("只有付费剧目趋势收面板")
        return self


class UniQuery(_DateRange):
    """全域报表列表。日期是区间，默认今天。"""

    series_name: str | None = Field(None, max_length=128, description="剧名，模糊。只对剧目两个 tab 生效")
    sort_by: str = Field("all_stat_cost_trend", description="排序字段，默认全域消耗")

    @model_validator(mode="after")
    def check_sort(self) -> UniQuery:
        if self.sort_by not in UNI_SORT_FIELDS:
            raise ValueError("排序字段不支持")
        return self


class UniSpeedQuery(BaseModel):
    """全域时速弹框：所选日与前一天按小时对比。"""

    model_config = ConfigDict(extra="forbid")

    scope: Literal["drama", "pitcher", "group"] = Field(
        description="drama 剧目行（菜单 13）、pitcher 投手行（菜单 14）、group 组行（菜单 15）"
    )
    id: int = Field(description="剧目为 manhua_series.id，投手为用户 id，组为部门 id")
    date: Date = Field(default_factory=_today, description="所选日，北京时间，默认今天")


class ManhuaMetrics(BaseModel):
    stat_cost: float = Field(description="消耗")
    stat_pay_amount: float = Field(description="付费金额，即回收")
    pay_amount_roi: float = Field(description="回收 ROI = 付费金额 / 消耗")
    attribution_game_in_app_ltv_1day: float = Field(description="当日付费金额")
    attribution_game_in_app_ltv_8days: float = Field(description="7 日付费金额")
    attribution_micro_game_0d_ltv: float = Field(description="当日广告变现 LTV")
    attribution_micro_game_7d_ltv: float = Field(description="7 日广告变现 LTV")
    attribution_game_in_app_roi_1day: float = Field(description="当日付费 ROI")
    attribution_game_in_app_roi_8days: float = Field(description="7 日付费 ROI")
    attribution_micro_game_0d_roi: float = Field(description="当日广告变现 ROI")
    attribution_micro_game_7d_roi: float = Field(description="7 日广告变现 ROI")
    show_cnt: int = Field(description="展示数")
    cpm_platform: float = Field(description="平均千次展现成本")
    click_cnt: int = Field(description="点击数")
    cpc_platform: float = Field(description="点击成本")
    active: int = Field(description="激活数")
    active_cost: float = Field(description="激活成本")
    convert_cnt: int = Field(description="转化数")
    conversion_cost: float = Field(description="转化成本")
    ctr: float = Field(description="点击率，百分数")
    active_rate: float = Field(description="激活率，百分数")
    conversion_rate: float = Field(description="转化率，百分数")


class ManhuaDramaItem(ManhuaMetrics):
    series_id: int
    book_name: str
    media: str
    drama_type: str
    channel: str
    bid_type: str
    panel: str
    drama_age: str
    teams: str
    pitchers: str
    promotion_with_cost_count: int


class ManhuaProjectItem(ManhuaMetrics):
    project_id: int
    project_name: str
    series_id: int
    book_name: str
    pitcher: str
    team: str
    created_at: str | None
    first_cost_time: str | None
    project_budget: float | None
    roi_goal: float | None


class ManhuaPromotionItem(ManhuaProjectItem):
    promotion_id: int
    promotion_name: str


class UniMetrics(BaseModel):
    all_stat_cost_trend: float
    all_roi_24h_trend: float
    all_stat_total_cost_trend: float
    all_gmv_trend: float
    all_billing_gmv_0day_trend: float
    all_billing_gmv_24h_trend: float
    all_billing_gmv_3days_trend: float = Field(description="三日全域 GMV（计费时间），三日 ROI 的分子")
    all_roi_trend: float
    all_roi_0day_trend: float
    all_roi_3days_trend: float
    all_income_trend: float
    all_income_0day_trend: float
    all_pay_amount_income_trend: float
    all_micro_game_income_trend: float
    new_project_count: int
    new_project_with_cost_count: int
    spending_project_count: int
    spending_advertiser_count: int


class UniDramaItem(UniMetrics):
    series_id: int
    book_name: str
    platform_name: str
    stat_time_day: str


class UniPitcherDramaItem(UniDramaItem):
    pitcher_user_id: int
    pitcher_name: str


class UniPitcherItem(UniMetrics):
    pitcher_user_id: int
    pitcher_name: str
    stat_time_day: str
    new_drama_count: int


class UniGroupItem(UniMetrics):
    department_id: int
    department_name: str
    stat_time_day: str
    new_drama_count: int


class ReportPage(BaseModel, Generic[T, S]):
    """分页加顶部汇总。汇总按筛选后的全部行算，不只当前页。"""

    items: Sequence[T] = Field(serialization_alias="list", validation_alias="list")
    total: int
    page: int
    page_size: int
    summary: S


class HourValue(BaseModel):
    hour: int = Field(description="小时 0–23，北京时间")
    stat_cost: float
    stat_pay_amount: float


class ManhuaTrendData(BaseModel):
    date: str
    items: list[HourValue]


class SpeedPoint(BaseModel):
    hour: int
    value: float


class SpeedRate(BaseModel):
    hour: int
    rate: float = Field(description="(本小时 - 前一天同小时) / 前一天同小时；前一天为 0 时为 0")


class SpeedSeries(BaseModel):
    current: list[SpeedPoint]
    previous: list[SpeedPoint]
    growth_rate: list[SpeedRate]


class UniSpeedData(BaseModel):
    date: str
    previous_date: str
    cost: SpeedSeries
    recovery: SpeedSeries
