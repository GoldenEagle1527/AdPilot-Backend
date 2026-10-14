"""巨量广告列表的入参和出参。多传字段一律 422。"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Annotated, Literal

from pydantic import BaseModel, BeforeValidator, ConfigDict, Field, model_validator


DeliveryKind = Literal["standard", "uni"]
ChargeMode = Literal["IAA", "IAP"]
SortOrder = Literal["asc", "desc"]
SortBy = Literal[
    "account_id",
    "balance",
    "stat_cost",
    "revenue_today",
    "revenue_total",
    "revenue_today_rate",
    "revenue_total_rate",
    "show_cnt",
    "cpm",
    "click_cnt",
    "ctr",
    "cpc",
]


class AccountQuery(BaseModel):
    """账户页。页签可传 standard 或 uni，不传则两种都展示。日期成对，含起止当天。"""

    model_config = ConfigDict(extra="forbid")

    page: int = Field(1, ge=1, description="页码，从 1 起")
    page_size: int = Field(20, ge=1, le=100, description="每页条数，最大 100")
    delivery_kind: DeliveryKind | None = Field(
        None, description="页签：standard 标准、uni 全域。不传则两种都展示"
    )
    date_start: date | None = Field(None, description="开始日期，含当天。须和结束日期一起传")
    date_end: date | None = Field(None, description="结束日期，含当天")
    pitcher_user_id: int | None = Field(None, description="投手用户 id，须带短剧投手标签")
    account_id: int | None = Field(None, description="账户 id，精确。即 advertiser_account.advertiser_id")
    account_name: str | None = Field(None, description="账户名，模糊")
    charge_mode: ChargeMode | None = Field(None, description="IAA 或 IAP。不传则该页签下两种都要")
    sort_by: SortBy = Field("account_id", description="点表头排序的列。只对这一次查询")
    sort_order: SortOrder = Field("asc", description="asc 正序、desc 倒序")

    @model_validator(mode="after")
    def dates_are_a_pair(self) -> AccountQuery:
        """日期要么都空，要么都有，并且开始不晚于结束。"""
        if (self.date_start is None) ^ (self.date_end is None):
            raise ValueError("日期须同时填写开始和结束")
        if self.date_start is not None and self.date_end is not None and self.date_start > self.date_end:
            raise ValueError("开始日期不能晚于结束日期")
        return self


class AccountItem(BaseModel):
    """一行账户。除数是 0 时比率是 0.00。"""

    account_id: int
    account_name: str
    balance: str | None
    stat_cost: str
    revenue_today: str
    revenue_total: str
    revenue_today_rate: str | None
    revenue_total_rate: str | None
    show_cnt: int
    cpm: str | None
    click_cnt: int
    ctr: str | None
    cpc: str | None


class ProjectQuery(BaseModel):
    """项目页。标准和全域都列出。短剧下拉的值是 manhua_series.id。"""

    model_config = ConfigDict(extra="forbid")

    page: int = Field(1, ge=1)
    page_size: int = Field(20, ge=1, le=100)
    date_start: date | None = None
    date_end: date | None = None
    pitcher_user_id: int | None = None
    project_name: str | None = None
    project_id: int | None = None
    account_id: int | None = None
    account_name: str | None = None
    charge_mode: ChargeMode | None = None
    series_id: int | None = None
    project_status: Literal["开启", "暂停"] | None = None
    sort_by: Literal[
        "project_id",
        "account_id",
        "budget",
        "stat_cost",
        "revenue_today",
        "revenue_total",
        "revenue_today_rate",
        "revenue_total_rate",
        "show_cnt",
        "cpm",
        "click_cnt",
        "ctr",
        "cpc",
        "convert_cnt",
        "convert_cost",
        "convert_rate",
        "active",
        "recycle_amount",
        "active_arpu",
        "active_cost",
    ] = "project_id"
    sort_order: SortOrder = "asc"

    @model_validator(mode="after")
    def dates_are_a_pair(self) -> ProjectQuery:
        """日期要么都空，要么都有。"""
        if (self.date_start is None) ^ (self.date_end is None):
            raise ValueError("日期须同时填写开始和结束")
        if self.date_start is not None and self.date_end is not None and self.date_start > self.date_end:
            raise ValueError("开始日期不能晚于结束日期")
        return self


class ProjectBatchResult(BaseModel):
    """批量改过的项目，以及跟着改掉的广告条数。看不了的项目不出现在这里。"""

    project_ids: list[int]
    promotion_count: int


class ProjectItem(BaseModel):
    """一行项目。标准和全域都在这里。除数是 0 时比率是 0.00。"""

    project_id: int
    project_name: str
    project_status: Literal["开启", "暂停"]
    account_id: int
    account_name: str
    budget: str | None
    stat_cost: str
    revenue_today: str
    revenue_total: str
    revenue_today_rate: str | None
    revenue_total_rate: str | None
    show_cnt: int
    cpm: str | None
    click_cnt: int
    ctr: str | None
    cpc: str | None
    convert_cnt: int
    convert_cost: str | None
    convert_rate: str | None
    active: int
    recycle_amount: str
    active_arpu: str | None
    active_cost: str | None
    promotion_links: list[str]


class ProjectBatchWrite(BaseModel):
    """批量开启、暂停或删除项目。下面的广告跟着改。"""

    model_config = ConfigDict(extra="forbid")

    project_ids: list[int] = Field(min_length=1, max_length=100)
    action: Literal["开启", "暂停", "删除"]


class ProjectBudgetWrite(BaseModel):
    """批量改项目目标预算。金额是元，最多两位小数。"""

    model_config = ConfigDict(extra="forbid")

    project_ids: list[int] = Field(min_length=1, max_length=100)
    budget: Decimal = Field(gt=0, max_digits=10, decimal_places=2)


class ProjectBudgetResult(BaseModel):
    """巨量接受并已写入本地的项目。"""

    project_ids: list[int]


class PromotionQuery(BaseModel):
    """广告页。推广外链按完整链接精确匹配。广告名称是下拉选中的全名。"""

    model_config = ConfigDict(extra="forbid")

    page: int = Field(1, ge=1)
    page_size: int = Field(20, ge=1, le=100)
    date_start: date | None = None
    date_end: date | None = None
    pitcher_user_id: int | None = None
    promotion_name: str | None = Field(None, description="下拉选中的广告名，全名一致")
    promotion_id: int | None = None
    promotion_status: Literal["投放中", "已暂停", "已被项目暂停"] | None = None
    account_id: int | None = None
    account_name: str | None = None
    project_id: int | None = None
    project_name: str | None = None
    promotion_link: str | None = None
    series_name: str | None = None
    series_id: int | None = None
    charge_mode: ChargeMode | None = None
    sort_by: Literal[
        "promotion_id",
        "project_id",
        "account_id",
        "book_id",
        "budget",
        "stat_cost",
        "revenue_today",
        "revenue_total",
        "revenue_today_rate",
        "revenue_total_rate",
        "show_cnt",
        "cpm",
        "click_cnt",
        "ctr",
        "cpc",
        "convert_cnt",
        "convert_cost",
        "convert_rate",
        "active",
        "active_cost",
        "recycle_amount",
        "active_arpu",
    ] = "promotion_id"
    sort_order: SortOrder = "asc"

    @model_validator(mode="after")
    def dates_are_a_pair(self) -> PromotionQuery:
        if (self.date_start is None) ^ (self.date_end is None):
            raise ValueError("日期须同时填写开始和结束")
        if self.date_start is not None and self.date_end is not None and self.date_start > self.date_end:
            raise ValueError("开始日期不能晚于结束日期")
        return self


class PromotionNameQuery(BaseModel):
    """广告名称下拉。只列出当前登录人能看到的未删除广告名。"""

    model_config = ConfigDict(extra="forbid")

    page: int = Field(1, ge=1)
    page_size: int = Field(20, ge=1, le=100)


class PromotionNameItem(BaseModel):
    """一个下拉选项。一个广告名称对应一条广告。"""

    promotion_name: str


class PromotionBatchWrite(BaseModel):
    """批量开启、暂停或删除广告。不改所属项目。"""

    model_config = ConfigDict(extra="forbid")

    promotion_ids: list[int] = Field(min_length=1, max_length=100)
    action: Literal["开启", "暂停", "删除"]


class PromotionBatchResult(BaseModel):
    """改过的广告。看不了的广告不出现在这里。"""

    promotion_ids: list[int]


class PromotionItem(BaseModel):
    """一行广告。父项目暂停时，状态是已被项目暂停。除数是 0 时比率是 0.00。"""

    promotion_id: int
    promotion_name: str
    promotion_status: Literal["投放中", "已暂停", "已被项目暂停"]
    project_id: int | None
    project_name: str | None
    series_name: str | None
    book_id: int | None
    account_id: int
    account_name: str
    promotion_links: list[str]
    budget: str | None
    stat_cost: str
    revenue_today: str
    revenue_total: str
    revenue_today_rate: str | None
    revenue_total_rate: str | None
    show_cnt: int
    cpm: str | None
    click_cnt: int
    ctr: str | None
    cpc: str | None
    convert_cnt: int
    convert_cost: str | None
    convert_rate: str | None
    active: int
    active_cost: str | None
    recycle_amount: str
    active_arpu: str | None
    reject_reasons: list[str]


class MaterialQuery(BaseModel):
    """素材页。日期单选。投手须带短剧投手标签。"""

    model_config = ConfigDict(extra="forbid")

    page: int = Field(1, ge=1)
    page_size: int = Field(20, ge=1, le=100)
    stat_date: date
    pitcher_user_id: int | None = None
    account_id: int | None = None
    account_name: str | None = None
    promotion_id: int | None = None
    material_id: int | None = Field(None, description="创意id，即头条素材id。巨量 material_id")
    sort_by: Literal[
        "material_id",
        "promotion_id",
        "project_id",
        "account_id",
        "stat_cost",
        "show_cnt",
        "click_cnt",
        "convert_cnt",
        "convert_cost",
        "ctr",
        "cpc",
        "convert_rate",
    ] = "material_id"
    sort_order: SortOrder = "asc"


class MaterialItem(BaseModel):
    """一行素材。同一天的小时行加总。material_id 在本页叫创意id，即头条素材id。"""

    material_id: int | None = Field(None, description="创意id，即头条素材id。来自素材库视频的 ocean_material_id")
    video_id: int | None = Field(None, description="我们自己的视频 id，material_videos.id")
    play_url: str | None = Field(None, description="可播放地址，素材库视频文件地址")
    poster_url: str | None = Field(None, description="第一帧地址。素材库没有单独存过封面时为空")
    material_name: str | None
    promotion_id: int | None = Field(None, description="所属计划 id，oe_promotion.promotion_id。投放表没有则为空")
    promotion_name: str | None
    project_id: int
    project_name: str | None
    account_id: int
    account_name: str
    stat_cost: str
    show_cnt: int
    click_cnt: int
    ctr: str | None
    cpc: str | None
    convert_cnt: int
    convert_cost: str | None
    convert_rate: str | None


class UniProjectQuery(BaseModel):
    """全域项目页。短剧下拉的值是 manhua_series.id。"""

    model_config = ConfigDict(extra="forbid")

    page: int = Field(1, ge=1)
    page_size: int = Field(20, ge=1, le=100)
    date_start: date | None = None
    date_end: date | None = None
    douyin_account_id: int | None = None
    pitcher_user_id: int | None = None
    subject_id: int | None = None
    account_id: int | None = None
    project_id: int | None = None
    series_id: int | None = None
    project_status: Literal["开启", "暂停"] | None = None
    sort_by: Literal["project_id", "stat_cost"] = "project_id"
    sort_order: SortOrder = "asc"

    @model_validator(mode="after")
    def dates_are_a_pair(self) -> UniProjectQuery:
        if (self.date_start is None) ^ (self.date_end is None):
            raise ValueError("日期须同时填写开始和结束")
        if self.date_start is not None and self.date_end is not None and self.date_start > self.date_end:
            raise ValueError("开始日期不能晚于结束日期")
        return self


class UniProjectItem(BaseModel):
    """一行全域项目。roi_goal 先是创建时填的系数。向巨量查到新值后更新。没填过且没查到是 -。"""

    project_id: int
    project_name: str
    project_status: Literal["开启", "暂停"]
    subject_name: str | None
    account_id: int
    account_name: str
    pitcher_user_id: int | None
    pitcher_name: str | None
    series_name: str | None
    douyin_aweme_id: str | None
    douyin_name: str | None
    stat_cost: str
    budget: str | None
    roi_goal: str | None
    created_at: str
    create_result: Literal["创建成功", "创建失败"]
    failure_reason: str | None


ACCOUNT_COLUMNS = (
    "account_name",
    "account_id",
    "balance",
    "stat_cost",
    "revenue_today",
    "revenue_total",
    "revenue_today_rate",
    "revenue_total_rate",
    "show_cnt",
    "cpm",
    "click_cnt",
    "ctr",
    "cpc",
)
PROJECT_COLUMNS = (
    "project_name",
    "project_id",
    "project_status",
    "show_cnt",
    "cpm",
    "stat_cost",
    "click_cnt",
    "ctr",
    "account_name",
    "budget",
    "revenue_today",
    "revenue_total",
    "revenue_today_rate",
    "revenue_total_rate",
    "convert_cnt",
    "convert_cost",
    "convert_rate",
    "active",
    "recycle_amount",
    "active_arpu",
    "active_cost",
    "cpc",
    "promotion_links",
    "account_id",
)
PROMOTION_COLUMNS = (
    "promotion_name",
    "promotion_id",
    "promotion_status",
    "stat_cost",
    "revenue_today",
    "revenue_total",
    "revenue_today_rate",
    "revenue_total_rate",
    "show_cnt",
    "cpm",
    "click_cnt",
    "ctr",
    "cpc",
    "convert_cnt",
    "convert_rate",
    "budget",
    "account_name",
    "convert_cost",
    "active",
    "active_cost",
    "recycle_amount",
    "active_arpu",
    "project_name",
    "project_id",
    "series_name",
    "promotion_links",
    "book_id",
    "account_id",
)
MATERIAL_COLUMNS = (
    "material_id",
    "material_name",
    "stat_cost",
    "convert_cnt",
    "convert_cost",
    "show_cnt",
    "click_cnt",
    "ctr",
    "cpc",
    "convert_rate",
    "promotion_id",
    "promotion_name",
    "project_id",
    "project_name",
    "account_id",
    "account_name",
)
MENU_COLUMNS: dict[int, tuple[str, ...]] = {
    32: ACCOUNT_COLUMNS,
    33: PROJECT_COLUMNS,
    34: PROMOTION_COLUMNS,
    35: MATERIAL_COLUMNS,
}


def _menu_id_from_query(value: object) -> object:
    """地址栏里的 menu_id 是文本。32 这类数字先转成整数，再核对是不是这四个菜单。"""
    if isinstance(value, str):
        text = value.strip()
        if text.isdigit():
            return int(text)
    return value


MenuId = Annotated[Literal[32, 33, 34, 35], BeforeValidator(_menu_id_from_query)]


class ColumnQuery(BaseModel):
    """读这个用户在这个菜单上的列。没存过则返回默认顺序。"""

    model_config = ConfigDict(extra="forbid")

    menu_id: MenuId


class ColumnWrite(BaseModel):
    """替换这个用户在这个菜单上的勾选和顺序。列名必须属于该菜单，不能重复。"""

    model_config = ConfigDict(extra="forbid")

    menu_id: Literal[32, 33, 34, 35]
    columns: list[str] = Field(min_length=1, max_length=40)
    fixed_columns: list[str] = Field(default_factory=list, description="右侧固定的列，最多 5 个，必须是已选列")

    @model_validator(mode="after")
    def columns_belong_to_the_menu(self) -> ColumnWrite:
        allowed = set(MENU_COLUMNS[self.menu_id])
        chosen = set(self.columns)
        if any(name not in allowed for name in self.columns):
            raise ValueError("列名不在该菜单")
        if len(self.columns) != len(chosen):
            raise ValueError("列名不能重复")
        if len(self.fixed_columns) > 5:
            raise ValueError("固定列最多5个")
        if len(self.fixed_columns) != len(set(self.fixed_columns)):
            raise ValueError("固定列不能重复")
        if any(name not in chosen for name in self.fixed_columns):
            raise ValueError("固定列必须是已选列")
        return self


class ColumnData(BaseModel):
    """当前用户在这个菜单上要展示的列，按展示顺序。"""

    menu_id: Literal[32, 33, 34, 35]
    columns: list[str]
    fixed_columns: list[str]


