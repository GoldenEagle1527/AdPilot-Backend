from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


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
    # 对外取值见 domain.enums.ROLE_KIND_*；此处必须是字面量才能进 OpenAPI。
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
    model_config = ConfigDict(extra="forbid")

    tag_ids: list[str]


class AddUserTagsRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    user_ids: list[str] = Field(min_length=1)
    tag_ids: list[str] = Field(min_length=1)


class SetUserRolesRequest(BaseModel):
    role_ids: list[str]


class SetUserDataScopeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    department_ids: list[str]


class ResetPasswordRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    password: str = Field(min_length=1)
    password_confirm: str = Field(min_length=1)

    @field_validator("password", "password_confirm", mode="before")
    @classmethod
    def _strip_password(cls, value: object) -> object:
        return value.strip() if isinstance(value, str) else value
