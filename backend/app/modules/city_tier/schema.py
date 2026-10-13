"""城市分级出参。"""

from __future__ import annotations

from pydantic import BaseModel, Field


class CityRef(BaseModel):
    """发展划分里点开后的一座城市。"""

    ocean_code: str
    name: str


class CityTierGroup(BaseModel):
    """一个等级下的城市。"""

    tier: str
    cities: list[CityRef]


class CityTierList(BaseModel):
    """按等级分组的城市。免费和付费模板共用。"""

    items: list[CityTierGroup] = Field(default_factory=list)
