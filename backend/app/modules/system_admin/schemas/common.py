from __future__ import annotations

from pydantic import BaseModel, Field


class Tag(BaseModel):
    id: str
    name: str


class RoleName(BaseModel):
    id: str
    name: str


class RoleBrief(BaseModel):
    id: str
    name: str
    assigned: bool
    assigned_at: str | None


class IdEnabled(BaseModel):
    id: str
    enabled: bool


class IdTags(BaseModel):
    id: str
    tags: list[Tag]


class TagList(BaseModel):
    items: list[Tag]


class RoleBriefList(BaseModel):
    items: list[RoleBrief]


class MenuIds(BaseModel):
    menu_ids: list[str]


class DepartmentIds(BaseModel):
    department_ids: list[str]


class PasswordResetData(BaseModel):
    reset: bool
    password: str


class DepartmentNode(BaseModel):
    id: str
    name: str
    parent_id: str | None
    sort: int
    enabled: bool
    tenant: str
    created_at: str
    tags: list[Tag]
    children: list[DepartmentNode] = Field(default_factory=list)


class DepartmentTree(BaseModel):
    items: list[DepartmentNode]


class MenuNodeOut(BaseModel):
    id: str
    name: str
    type: str
    parent_id: str | None
    business_domain: str | None
    tenant_kind: str | None
    assigned_roles: list[RoleName] | None = None
    children: list[MenuNodeOut] = Field(default_factory=list)


class MenuTree(BaseModel):
    items: list[MenuNodeOut]


class UserListItem(BaseModel):
    id: str
    nickname: str
    login_account: str
    short_name: str | None
    phone: str | None
    enabled: bool
    department_id: str
    department_name: str
    role_kind: str
    remark: str | None
    tenant: str
    created_at: str
    tags: list[Tag]
    user_roles: list[RoleName]
    department_roles: list[RoleName]
    data_scope: list[RoleName]


class UserRolesData(BaseModel):
    items: list[RoleBrief]
    department_roles: list[RoleName]


DepartmentNode.model_rebuild()
MenuNodeOut.model_rebuild()
