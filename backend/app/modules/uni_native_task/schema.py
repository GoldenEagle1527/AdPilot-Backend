"""端原生投放任务的入参和出参。多传字段一律 422。"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Annotated, Any

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

LinkText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=2048)]
BatchTitle = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=512)]


class TaskQuery(BaseModel):
    """任务列表。只查当前投手自己的。日期段按创建日，左闭右闭。"""

    model_config = ConfigDict(extra="forbid")

    page: int = Field(1, ge=1, description="页码，从 1 起")
    page_size: int = Field(20, ge=1, le=100, description="每页条数，最大 100")
    date_start: date | None = Field(None, description="创建日期起，含当天，北京时间")
    date_end: date | None = Field(None, description="创建日期止，含当天，北京时间")
    series_name: str | None = Field(None, description="剧名，模糊")

    @model_validator(mode="after")
    def check_dates(self) -> TaskQuery:
        """起日不能晚于止日。"""
        if self.date_start is not None and self.date_end is not None and self.date_start > self.date_end:
            raise ValueError("日期段起不能晚于止")
        return self


class AccountPair(BaseModel):
    """一个全域抖音号配一个广告账户。"""

    model_config = ConfigDict(extra="forbid")

    douyin_account_id: int = Field(description="全域抖音号 id，须已分给当前投手")
    advertiser_id: int = Field(description="巨量广告主 id，即 advertiser_account.advertiser_id")


class PromotionLinkWrite(BaseModel):
    """一条推广链文本。不从剧场表带出。"""

    model_config = ConfigDict(extra="forbid")

    charge_mode: str = Field(pattern="^(IAA|IAP)$", description="IAA 免费、IAP 付费")
    link_text: LinkText = Field(description="推广链文本")


class TaskWrite(BaseModel):
    """新建或整表保存。预算和 ROI 不传则抄模板。状态不收，固定为已保存未提交。"""

    model_config = ConfigDict(extra="forbid")

    template_id: int = Field(description="全域模板 id")
    series_id: int = Field(description="短剧 manhua_series.id")
    project_budget: Decimal | None = Field(
        None, gt=0, le=Decimal("99999999.99"), max_digits=10, decimal_places=2, description="项目预算。不传则抄模板"
    )
    roi_coefficient: Decimal | None = Field(
        None, ge=0, le=Decimal("9999.999"), max_digits=7, decimal_places=3, description="ROI 系数。不传则抄模板"
    )
    accounts: list[AccountPair] = Field(min_length=1, max_length=50, description="抖音号与账户一一对应，至少一行")
    promotion_links: list[PromotionLinkWrite] = Field(
        default_factory=list, max_length=50, description="IAA / IAP 推广链文本，可空"
    )
    video_ids: list[int] = Field(
        default_factory=list, max_length=200, description="视频素材 id。素材表不存在时不能传"
    )
    title_ids: list[int] = Field(
        default_factory=list, max_length=100, description="自己标题库里的标题 id。标题库不存在时不能传"
    )
    batch_titles: list[BatchTitle] = Field(
        default_factory=list, max_length=100, description="临时标题。不写入标题库"
    )

    @model_validator(mode="after")
    def reject_duplicates(self) -> TaskWrite:
        """同一任务里抖音号、账户、视频、标题库 id 都不能重复。"""
        douyin_ids = [item.douyin_account_id for item in self.accounts]
        advertiser_ids = [item.advertiser_id for item in self.accounts]
        if len(douyin_ids) != len(set(douyin_ids)):
            raise ValueError("抖音号重复")
        if len(advertiser_ids) != len(set(advertiser_ids)):
            raise ValueError("账户重复")
        if len(self.video_ids) != len(set(self.video_ids)):
            raise ValueError("视频重复")
        if len(self.title_ids) != len(set(self.title_ids)):
            raise ValueError("标题重复")
        return self


class AccountItem(BaseModel):
    """任务里的一行抖音号和账户。"""

    douyin_account_id: str
    aweme_id: str
    douyin_name: str
    advertiser_account_id: str
    advertiser_id: int
    name: str


class PromotionLinkItem(BaseModel):
    """任务里的一条推广链。"""

    charge_mode: str
    link_text: str


class VideoRef(BaseModel):
    """任务里的一条视频。"""

    id: str
    name: str


class TitleRef(BaseModel):
    """任务里从标题库选来的一条标题。"""

    id: str
    title: str


class TaskItem(BaseModel):
    """一条任务。时间为北京时间，精确到秒。状态为 saved、running 或 done。"""

    id: str
    template_id: str
    template_name: str
    project_budget: str
    roi_coefficient: str
    pitcher_user_id: str
    series_id: str
    book_name: str
    series_short_name: str
    accounts: list[AccountItem]
    promotion_links: list[PromotionLinkItem]
    videos: list[VideoRef]
    titles: list[TitleRef]
    batch_titles: list[str]
    status: str
    executed_at: str | None
    created_at: str
    updated_at: str


class DeletedItem(BaseModel):
    """软删后的出参。"""

    id: str
    deleted: bool


class SubmitAccount(BaseModel):
    """一个抖音号和账户上的项目、一条广告报文。"""

    douyin_account_id: str
    aweme_id: str
    advertiser_id: int
    project_id: int
    product_id: int
    image_id: str
    project: dict[str, Any]
    promotions: list[dict[str, Any]]


class SubmitResult(BaseModel):
    """确认提交的结果。done 只表示假客户端结束，素材不算巨量已上传。"""

    id: str
    status: str
    executed_at: str | None
    materials_uploaded: bool
    promotion_links: list[PromotionLinkItem]
    accounts: list[SubmitAccount]
