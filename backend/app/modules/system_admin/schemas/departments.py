from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.core.times import iso8601_z
from app.modules.system_admin.domain import Department, DepartmentTag, Role
from app.modules.system_admin.schemas.common import RoleName


def tag_item(tag: DepartmentTag) -> dict[str, str]:
    return {"id": tag.id, "name": tag.name}


def department_node(dept: Department, *, children: list[dict] | None = None) -> dict:
    tags = [tag_item(t) for t in sorted(dept.tags, key=lambda t: (t.name, t.id))]
    roles = [
        RoleName(id=role.id, name=role.name).model_dump()
        for role in sorted(dept.roles, key=lambda r: (r.name, r.id))
    ]
    return {
        "id": dept.id,
        "name": dept.name,
        "parent_id": dept.parent_id,
        "sort": dept.sort,
        "enabled": bool(dept.enabled),
        "tenant": dept.tenant,
        "created_at": iso8601_z(dept.created_at),
        "tags": tags,
        "roles": roles,
        "children": [] if children is None else children,
    }


def role_brief(role: Role, assigned: bool, assigned_at: datetime | None) -> dict:
    return {
        "id": role.id,
        "name": role.name,
        "assigned": assigned,
        "assigned_at": iso8601_z(assigned_at) if assigned_at is not None else None,
    }


def filter_departments(
    depts: list[Department],
    name: str | None,
    enabled: bool | None,
    department_id: str | None = None,
) -> list[Department]:
    if enabled is not None:
        pool = [d for d in depts if d.enabled == enabled]
    else:
        pool = list(depts)
    pool = [d for d in pool if d.deleted_at is None]

    by_id = {d.id: d for d in depts}
    children_of: dict[str | None, list[Department]] = {}
    for dept in depts:
        if dept.deleted_at is not None:
            continue
        children_of.setdefault(dept.parent_id, []).append(dept)

    if department_id:
        target = by_id.get(department_id)
        if target is None or target.deleted_at is not None:
            return []
        keep: set[str] = {department_id}
        stack = [department_id]
        while stack:
            current = stack.pop()
            for child in children_of.get(current, []):
                if child.id not in keep:
                    keep.add(child.id)
                    stack.append(child.id)
        cursor = target.parent_id
        while cursor:
            keep.add(cursor)
            parent = by_id.get(cursor)
            cursor = parent.parent_id if parent is not None else None
        pool = [d for d in pool if d.id in keep]

    if not name:
        return pool

    needle = name.casefold()
    by_parent: dict[str | None, list[Department]] = {}
    for dept in pool:
        by_parent.setdefault(dept.parent_id, []).append(dept)
    pool_ids = {d.id for d in pool}

    def subtree_matches(dept: Department) -> bool:
        if needle in dept.name.casefold():
            return True
        for child in by_parent.get(dept.id, []):
            if child.id in pool_ids and subtree_matches(child):
                return True
        return False

    return [d for d in pool if subtree_matches(d)]


def build_department_tree(depts: list[Department]) -> list[dict]:
    ids = {d.id for d in depts}
    nodes = {d.id: department_node(d, children=[]) for d in depts}
    roots: list[dict] = []
    for dept in depts:
        node = nodes[dept.id]
        parent_id = dept.parent_id
        if parent_id is not None and parent_id in ids:
            nodes[parent_id]["children"].append(node)
        else:
            roots.append(node)

    def sort_nodes(items: list[dict]) -> None:
        items.sort(key=lambda n: (n["sort"], n["id"]))
        for item in items:
            sort_nodes(item["children"])

    sort_nodes(roots)
    return roots


class CreateDepartmentBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1)
    parent_id: str | None = None
    sort: int = 0
    tenant: str | None = None


class UpdateDepartmentBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1)
    parent_id: str | None
    sort: int


class SetDepartmentStatusBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    enabled: bool


class CreateDepartmentTagBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1)


class SetDepartmentTagsBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tag_ids: list[str]


class AddDepartmentTagsBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    department_ids: list[str] = Field(min_length=1)
    tag_ids: list[str] = Field(min_length=1)


class SetDepartmentRolesBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    role_ids: list[str]
