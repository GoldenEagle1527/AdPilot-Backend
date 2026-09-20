from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ManhuaSeriesItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    playlet_id: str
    book_id: str
    category_text: str
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


class ListManhuaSeriesQuery(BaseModel):
    model_config = ConfigDict(extra="forbid")

    category_text: str | None = None
    book_name: str | None = None
    estimate_publish_time_from: datetime | None = None
    estimate_publish_time_to: datetime | None = None
    collected_at_from: datetime | None = None
    collected_at_to: datetime | None = None
    publish_status: int | None = Field(default=None)
    listed_today: bool | None = None
    department_id: str | None = None
    episode_amount_min: int | None = None
    episode_amount_max: int | None = None
