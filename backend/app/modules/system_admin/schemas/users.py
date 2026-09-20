from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, Field, field_validator


def iso8601_z(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    else:
        value = value.astimezone(timezone.utc)
    return value.isoformat().replace("+00:00", "Z")


def _blank_to_none(value: str | None) -> str | None:
    if value is None:
        return None
    stripped = value.strip()
    return stripped or None


class CreateUserRequest(BaseModel):
    nickname: str = Field(min_length=1)
    login_account: str = Field(min_length=1)
    short_name: str | None = None
    password: str | None = None
    phone: str | None = None
    department_id: str = Field(min_length=1)
    remark: str | None = Field(default=None, max_length=200)
    tenant: str | None = None

    @field_validator("nickname", "login_account", "department_id", mode="before")
    @classmethod
    def _strip_required(cls, value: object) -> object:
        return value.strip() if isinstance(value, str) else value

    @field_validator("short_name", "phone", "remark", "tenant", "password", mode="before")
    @classmethod
    def _optional_str(cls, value: object) -> object:
        if isinstance(value, str):
            return _blank_to_none(value)
        return value


class UpdateUserRequest(BaseModel):
    nickname: str = Field(min_length=1)
    short_name: str | None = None
    phone: str | None = None
    department_id: str = Field(min_length=1)
    role_kind: Literal["负责人", "成员"]
    remark: str | None = Field(default=None, max_length=200)

    @field_validator("nickname", "department_id", mode="before")
    @classmethod
    def _strip_required(cls, value: object) -> object:
        return value.strip() if isinstance(value, str) else value

    @field_validator("short_name", "phone", "remark", mode="before")
    @classmethod
    def _optional_str(cls, value: object) -> object:
        if isinstance(value, str):
            return _blank_to_none(value)
        return value


class SetUserStatusRequest(BaseModel):
    enabled: bool


class CreateUserTagRequest(BaseModel):
    name: str = Field(min_length=1)

    @field_validator("name")
    @classmethod
    def _strip_name(cls, value: str) -> str:
        return value.strip()


class SetUserTagsRequest(BaseModel):
    tag_ids: list[str]


class SetUserRolesRequest(BaseModel):
    role_ids: list[str]


class SetUserDataScopeRequest(BaseModel):
    department_ids: list[str]
