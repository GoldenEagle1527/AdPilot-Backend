"""巨量账户、授权、项目、上传、报表与关停的入参和出参。"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class OrganizationItem(BaseModel):
    """一条授权组织。"""

    advertiser_id: int
    advertiser_name: str
    account_role: str
    ocean_version: str


class OrganizationList(BaseModel):
    """不分页的组织列表。"""

    items: list[OrganizationItem]


class AdvertiserItem(BaseModel):
    """一条广告主，含余额（元）和公司名。"""

    account_id: int
    account_name: str
    valid_balance: float
    adv_company_name: str
    organization_id: int


class AdvertiserQuery(BaseModel):
    """广告主分页查询。"""

    model_config = ConfigDict(extra="forbid")

    page: int = Field(1, ge=1, description="页码，从 1 起")
    page_size: int = Field(20, ge=1, le=100, description="每页条数，最大 100")
    account_name: str | None = Field(None, description="账户名称，模糊")
    account_id: int | None = Field(None, description="账户 id，精确")


class AuthorizeQuery(BaseModel):
    """授权链接渠道。"""

    model_config = ConfigDict(extra="forbid")

    channel: Literal["third", "self"]


class AuthorizeData(BaseModel):
    """授权页地址。"""

    authorize_url: str


class OAuthCallbackQuery(BaseModel):
    """授权回调。state 可空，auth_code 不可空。"""

    model_config = ConfigDict(extra="forbid")

    auth_code: str = Field(min_length=1)
    state: str = ""


class OAuthTokenData(BaseModel):
    """换票结果。"""

    access_token: str
    refresh_token: str


class ProjectCreate(BaseModel):
    """创建项目。delivery_mode 只允许手动或自动投放。"""

    model_config = ConfigDict(extra="forbid")

    advertiser_id: int
    name: str = Field(min_length=1)
    landing_type: str = Field(min_length=1)
    marketing_goal: str = Field(min_length=1)
    ad_type: str = Field(min_length=1)
    delivery_mode: Literal["MANUAL", "PROCEDURAL"]
    subject_id: int
    template: dict[str, Any] | None = None


class ProjectItem(ProjectCreate):
    """已创建的项目。"""

    project_id: int


class VideoCreate(BaseModel):
    """上传视频。"""

    model_config = ConfigDict(extra="forbid")

    advertiser_id: int
    video_url: str = Field(min_length=1)


class VideoItem(VideoCreate):
    """已登记的视频。"""

    video_id: str
    status: str


class ProductCreate(BaseModel):
    """商品库上传一条剧。"""

    model_config = ConfigDict(extra="forbid")

    drama_name: str = Field(min_length=1)
    file_url: str = Field(min_length=1)


class ProductItem(ProductCreate):
    """已登记的商品。"""

    library_id: int
    product_id: int


class ReportItem(BaseModel):
    """一条广告报表。回收率字段沿用巨量指标名。"""

    promotion_id: int
    stat_cost: float
    attribution_micro_game_0d_roi: float
    advertiser_id: int


class ReportList(BaseModel):
    """不分页的报表。"""

    items: list[ReportItem]


class PromotionStatusBody(BaseModel):
    """批量改广告启停。"""

    model_config = ConfigDict(extra="forbid")

    advertiser_id: int
    promotion_ids: list[int] = Field(min_length=1)
    opt_status: Literal["DISABLE", "ENABLE"]


class PromotionStatusItem(BaseModel):
    """一条广告的目标状态。"""

    promotion_id: int
    opt_status: str


class PromotionStatusList(BaseModel):
    """批量改状态的结果。"""

    items: list[PromotionStatusItem]


class AutoPauseBody(BaseModel):
    """按报表阈值关停。operator 目前只接受小于等于。"""

    model_config = ConfigDict(extra="forbid")

    metric: Literal["stat_cost", "roi"]
    operator: Literal["lte"]
    threshold: float


class AutoPauseResult(BaseModel):
    """命中关停与保留的广告 id。"""

    paused: list[int]
    kept: list[int]
