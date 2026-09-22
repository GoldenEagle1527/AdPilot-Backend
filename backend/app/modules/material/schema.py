"""漫剧库列表的入参和出参。"""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Literal

from pydantic import AfterValidator, BaseModel, BeforeValidator, ConfigDict, Field, model_validator

from app.core.times import BEIJING

_STAMP = "%Y-%m-%d %H:%M:%S"


def ensure_beijing_stamp(value: str) -> str:
    """入参时间只收 YYYY-MM-DD HH:MM:SS。"""
    try:
        datetime.strptime(value, _STAMP)
    except ValueError as exc:
        raise ValueError("时间格式为 YYYY-MM-DD HH:MM:SS") from exc
    return value


BeijingStamp = Annotated[str, AfterValidator(ensure_beijing_stamp)]


def ensure_collected_at(value: str) -> datetime:
    """采集时间入参收成北京时间。格式不对就拒绝。"""
    try:
        parsed = datetime.strptime(value, _STAMP)
    except ValueError as exc:
        raise ValueError("时间格式为 YYYY-MM-DD HH:MM:SS") from exc
    return parsed.replace(tzinfo=BEIJING)


CollectedAt = Annotated[datetime, BeforeValidator(ensure_collected_at)]


class ManhuaSeriesQuery(BaseModel):
    """漫剧库列表查询。时间只收 YYYY-MM-DD HH:MM:SS。"""

    model_config = ConfigDict(extra="forbid")

    page: int = Field(1, ge=1, description="页码，从 1 起")
    page_size: int = Field(20, ge=1, le=100, description="每页条数，最大 100")
    tab_text: Literal["IAA", "IAP"] | None = Field(None, description="tab，IAA 或 IAP，不传为全部")
    book_name: str | None = Field(None, description="短剧名称，模糊")
    estimate_publish_time_from: BeijingStamp | None = Field(
        None, description="预估可投起，YYYY-MM-DD HH:MM:SS，左闭"
    )
    estimate_publish_time_to: BeijingStamp | None = Field(
        None, description="预估可投止，YYYY-MM-DD HH:MM:SS，右闭"
    )
    collected_at_from: CollectedAt | None = Field(None, description="采集时间起，YYYY-MM-DD HH:MM:SS，左闭")
    collected_at_to: CollectedAt | None = Field(None, description="采集时间止，YYYY-MM-DD HH:MM:SS，右闭")
    publish_status: Literal[1, 2] | None = Field(None, description="1 未发布、2 已发布，不传为全部")
    listed_today: bool | None = Field(None, description="是否当天上架，不传为全部")
    department_id: str | None = Field(None, description="部门。本轮传入则结果为空")
    episode_amount_min: int | None = Field(None, ge=0, description="集数下限，含")
    episode_amount_max: int | None = Field(None, ge=0, description="集数上限，含")

    @model_validator(mode="after")
    def check_ranges(self) -> ManhuaSeriesQuery:
        """结束时间不能早于开始，集数上限不能小于下限。"""
        if (
            self.estimate_publish_time_from is not None
            and self.estimate_publish_time_to is not None
            and self.estimate_publish_time_to < self.estimate_publish_time_from
        ):
            raise ValueError("预估可投结束时间不能早于开始时间")
        if (
            self.collected_at_from is not None
            and self.collected_at_to is not None
            and self.collected_at_to < self.collected_at_from
        ):
            raise ValueError("采集结束时间不能早于开始时间")
        if (
            self.episode_amount_min is not None
            and self.episode_amount_max is not None
            and self.episode_amount_max < self.episode_amount_min
        ):
            raise ValueError("集数上限不能小于下限")
        return self


class ManhuaSeriesItem(BaseModel):
    """一条已落库短剧。tab_text 为 IAA 或 IAP，部门本轮恒空。"""

    id: str
    playlet_id: str
    book_id: str
    category_text: str
    tab_text: str
    thumb_url: str
    book_name: str
    episode_amount: int
    department_name: str | None
    publish_status: int
    delivery_status: bool
    publish_time: str
    estimate_publish_time: str
    create_time: str
    collected_at: str
    douyin_nick_name: str
