"""三方剧场的入参和出参。"""

from __future__ import annotations

from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

from app.modules.theater.model import DeliveryMode, TheaterStyle, TheaterType

AppName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=128)]
AdSource = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=64)]


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
