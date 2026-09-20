from __future__ import annotations

from pydantic import BaseModel, Field


class SessionMe(BaseModel):
    id: str
    nickname: str
    login_account: str
    short_name: str | None
    phone: str | None
    enabled: bool
    department_id: str
    department_name: str
    role_kind: str
    tenant: str
    remark: str | None


class SessionMenuNode(BaseModel):
    id: str
    name: str
    type: str
    parent_id: str | None
    business_domain: str | None
    tenant_kind: str | None
    children: list[SessionMenuNode] = Field(default_factory=list)


class SessionMenus(BaseModel):
    items: list[SessionMenuNode]


class SessionDataScope(BaseModel):
    department_ids: list[str]
    self_only: bool
    user_id: str
