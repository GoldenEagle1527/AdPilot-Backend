from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.modules.system_admin.schemas.common import AssignedUser, RoleName


def iso_z(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    else:
        value = value.astimezone(timezone.utc)
    return value.isoformat().replace("+00:00", "Z")


class RoleListItem(BaseModel):
    id: str
    name: str
    remark: str | None
    enabled: bool
    created_at: str
    updated_at: str
    updated_by: str | None
    assigned_user_count: int
    assigned_department_count: int
    assigned_users: list[AssignedUser]
    assigned_departments: list[RoleName]


class CreateRoleBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=64)
    remark: str | None = Field(default=None, max_length=200)


class UpdateRoleBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=64)
    remark: str | None = Field(default=None, max_length=200)


class SetRoleStatusBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    enabled: bool


class SetRoleMenusBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    menu_ids: list[str]


def role_item_dict(
    role: Any,
    assigned_users: list[AssignedUser] | None = None,
    assigned_departments: list[RoleName] | None = None,
) -> dict[str, Any]:
    users = assigned_users or []
    depts = assigned_departments or []
    return RoleListItem(
        id=role.id,
        name=role.name,
        remark=role.remark,
        enabled=role.enabled,
        created_at=iso_z(role.created_at),
        updated_at=iso_z(role.updated_at),
        updated_by=role.updated_by,
        assigned_user_count=len(users),
        assigned_department_count=len(depts),
        assigned_users=users,
        assigned_departments=depts,
    ).model_dump()
