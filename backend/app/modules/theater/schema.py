"""三方剧场的入参和出参。"""

from __future__ import annotations

from datetime import date
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

from app.modules.material.schema import BeijingTime
from app.modules.theater.model import DeliveryMode, TheaterStyle, TheaterType

AppName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=128)]
AdSource = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=64)]
TemplateName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=128)]
PromotionUrl = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=2048)]


class PlatformQuery(BaseModel):
    """平台列表查询。平台名称和启用状态都不传为全部。"""

    model_config = ConfigDict(extra="forbid")

    page: int = Field(1, ge=1, description="页码，从 1 起")
    page_size: int = Field(20, ge=1, le=100, description="每页条数，最大 100")
    name: str | None = Field(None, description="平台名称，模糊，不传为全部")
    is_enabled: bool | None = Field(None, description="启用状态：true 启用、false 禁用，不传为全部")


class PlatformItem(BaseModel):
    """一个平台。时间为北京时间 +08:00，精确到秒。"""

    id: str
    name: str
    code: str
    sort_order: int
    is_enabled: bool
    supports_mini_program: bool
    supports_native: bool
    created_at: str
    updated_at: str


class PlatformUpdate(BaseModel):
    """改平台入参：只准改启用状态和两个剧场类型开关，至少传一个，不传的不动。"""

    model_config = ConfigDict(extra="forbid")

    is_enabled: bool | None = Field(None, description="启用状态：true 启用、false 禁用")
    supports_mini_program: bool | None = Field(None, description="是否支持小程序")
    supports_native: bool | None = Field(None, description="是否支持端原生")

    @model_validator(mode="after")
    def require_one_field(self) -> PlatformUpdate:
        """一个字段都没给、或给的全是 null，都当没改，直接拒绝。"""
        if not self.model_dump(exclude_none=True):
            raise ValueError("至少修改一项")
        return self


class AppQuery(BaseModel):
    """应用列表查询。五个筛选都是下拉单选，不传为全部。"""

    model_config = ConfigDict(extra="forbid")

    page: int = Field(1, ge=1, description="页码，从 1 起")
    page_size: int = Field(20, ge=1, le=100, description="每页条数，最大 100")
    platform_id: int | None = Field(None, description="平台 id，不传为全部")
    theater_type: TheaterType | None = Field(
        None, description="剧场类型：mini_program 小程序、native 端原生，不传为全部"
    )
    delivery_mode: DeliveryMode | None = Field(None, description="投放模式：IAA、IAP，不传为全部")
    style: TheaterStyle | None = Field(None, description="剧场风格：live_action 真人剧、manhua 漫剧，不传为全部")
    is_valid: bool | None = Field(None, description="状态：true 有效、false 无效，不传为全部")


class AppItem(BaseModel):
    """一个应用。时间为北京时间 +08:00，精确到秒。"""

    id: str
    platform_id: str
    platform_name: str
    name: str
    theater_type: str
    delivery_mode: str
    style: str
    ad_source: str
    is_valid: bool
    created_at: str
    updated_at: str


class AppCreate(BaseModel):
    """新增应用入参。状态不收，新增一律有效。"""

    model_config = ConfigDict(extra="forbid")

    platform_id: int = Field(description="平台 id，须是启用且支持所选剧场类型的平台")
    name: AppName = Field(description="剧场名称，去首尾空白，1–128 字，同平台不重名")
    theater_type: TheaterType = Field(description="剧场类型：mini_program 小程序、native 端原生")
    delivery_mode: DeliveryMode = Field(description="投放模式，单选：IAA、IAP")
    style: TheaterStyle = Field(description="剧场风格：live_action 真人剧、manhua 漫剧")
    ad_source: AdSource = Field(description="广告来源名称，去首尾空白，1–64 字")


class AppStatusUpdate(BaseModel):
    """改应用状态入参：只收状态，其它字段不可改。"""

    model_config = ConfigDict(extra="forbid")

    is_valid: bool = Field(description="状态：true 有效、false 无效")


class PromotionTaskQuery(BaseModel):
    """推广链同步任务列表查询。只查爬虫处理中、成功、失败三种，没到点和排队中的不出现。"""

    model_config = ConfigDict(extra="forbid")

    page: int = Field(1, ge=1, description="页码，从 1 起")
    page_size: int = Field(20, ge=1, le=100, description="每页条数，最大 100")
    book_name: str | None = Field(None, description="短剧名称，模糊，不传为全部")
    status: Literal["running", "success", "failed"] | None = Field(
        None, description="状态：running 爬虫处理中、success 成功、failed 失败，不传为全部"
    )
    execute_at_from: BeijingTime | None = Field(None, description="执行时间起，YYYY-MM-DD HH:MM:SS，左闭")
    execute_at_to: BeijingTime | None = Field(None, description="执行时间止，YYYY-MM-DD HH:MM:SS，右闭")

    @model_validator(mode="after")
    def check_range(self) -> PromotionTaskQuery:
        """执行时间止不能早于起。"""
        if (
            self.execute_at_from is not None
            and self.execute_at_to is not None
            and self.execute_at_to < self.execute_at_from
        ):
            raise ValueError("执行结束时间不能早于开始时间")
        return self


class PromotionTaskItem(BaseModel):
    """一条推广链同步任务。时间为北京时间 +08:00，精确到秒。"""

    id: str
    series_id: str
    book_name: str
    collector_name: str
    tab_text: str
    category_text: str
    status: str
    reason: str
    execute_at: str
    finished_at: str | None


class PromotionLinkQuery(BaseModel):
    """端原生推广链列表查询。筛选都不传为全部。"""

    model_config = ConfigDict(extra="forbid")

    page: int = Field(1, ge=1, description="页码，从 1 起")
    page_size: int = Field(20, ge=1, le=100, description="每页条数，最大 100")
    publish_date_from: date | None = Field(None, description="首发日期起，YYYY-MM-DD，左闭")
    publish_date_to: date | None = Field(None, description="首发日期止，YYYY-MM-DD，右闭")
    theater_app_id: int | None = Field(None, description="剧场，应用 id，不传为全部")
    series_id: int | None = Field(None, description="剧名，漫剧流转剧库 id，不传为全部")
    is_enabled: bool | None = Field(None, description="启用状态：true 启用、false 停用，不传为全部")

    @model_validator(mode="after")
    def check_range(self) -> PromotionLinkQuery:
        """首发日期止不能早于起。"""
        if (
            self.publish_date_from is not None
            and self.publish_date_to is not None
            and self.publish_date_to < self.publish_date_from
        ):
            raise ValueError("首发结束日期不能早于开始日期")
        return self


class PromotionLinkItem(BaseModel):
    """一条端原生推广链。时间为北京时间 +08:00，精确到秒。"""

    id: str
    theater_app_id: str | None
    theater_app_name: str | None
    series_id: str
    book_name: str
    is_enabled: bool
    recharge_template_name: str
    publish_time: str | None
    promotion_url: str
    promotion_create_time: str | None


class PromotionCollectCreate(BaseModel):
    """批量采集：选一部短剧，指定执行时间和付费类型。只建任务，不在这次请求里调常读。"""

    model_config = ConfigDict(extra="forbid")

    series_id: int = Field(ge=1, description="短剧，漫剧流转剧库主键。book_id 从剧库取")
    execute_at: BeijingTime = Field(description="执行时间，YYYY-MM-DD HH:MM:SS，到点才拉推广链")
    charge_type: Literal["all", "paid", "free"] = Field(
        "all", description="付费类型：all 全部、paid 付费、free 免费，默认全部"
    )


class PromotionCollectResult(BaseModel):
    """刚建好的手动采集任务。状态是 pending，列表在开始执行前不展示它。"""

    id: str
    series_id: str
    book_name: str
    collector_name: str
    charge_type: str
    status: str
    execute_at: str


class PromotionLinkCreate(BaseModel):
    """人工新增：选短剧，五个档位各填 URL；剧场按档位 IAA/IAP 自动挂应用，空档不建行，至少一条。"""

    model_config = ConfigDict(extra="forbid")

    series_id: int = Field(description="剧名，漫剧流转剧库主键")
    iaa: str | None = Field(None, description="IAA 推广链")
    medium: str | None = Field(None, description="中额推广链")
    small: str | None = Field(None, description="小额推广链")
    extra_small: str | None = Field(None, description="超小额推广链")
    ultra_small: str | None = Field(None, description="超超小额推广链")

    @model_validator(mode="after")
    def filled_urls(self) -> PromotionLinkCreate:
        """空白当未填；非空须 1–2048 字；至少一个档位有 URL。"""
        has_url = False
        for field in ("iaa", "medium", "small", "extra_small", "ultra_small"):
            raw = getattr(self, field)
            if raw is None:
                continue
            url = raw.strip()
            if not url:
                setattr(self, field, None)
                continue
            if len(url) > 2048:
                raise ValueError(f"{field} 最长 2048 字")
            setattr(self, field, url)
            has_url = True
        if not has_url:
            raise ValueError("至少填写一条推广链")
        return self


class PromotionLinkCreateResult(BaseModel):
    """人工新增出参：本次新建的行。"""

    items: list[PromotionLinkItem]


class PromotionLinkUpdate(BaseModel):
    """编辑推广链：剧名不可改，其它都可改。只改传了的字段，至少传一个；剧场传 null 为清空。"""

    model_config = ConfigDict(extra="forbid")

    theater_app_id: int | None = Field(None, description="剧场，应用 id；传 null 清空")
    is_enabled: bool | None = Field(None, description="启用状态：true 启用、false 停用")
    recharge_template_name: TemplateName | None = Field(None, description="出价面板，去首尾空白，1–128 字")
    publish_time: BeijingTime | None = Field(None, description="首发时间，YYYY-MM-DD HH:MM:SS")
    promotion_url: PromotionUrl | None = Field(None, description="推广链，去首尾空白，1–2048 字")
    promotion_create_time: BeijingTime | None = Field(None, description="创建时间，YYYY-MM-DD HH:MM:SS")

    @model_validator(mode="after")
    def check_fields(self) -> PromotionLinkUpdate:
        """至少改一项；除剧场外的字段不能传 null。"""
        if not self.model_fields_set:
            raise ValueError("至少修改一项")
        nulls = sorted(k for k in self.model_fields_set - {"theater_app_id"} if getattr(self, k) is None)
        if nulls:
            raise ValueError(f"不能为空：{', '.join(nulls)}")
        return self
