from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.core.times import beijing_iso
from app.modules.system_admin.domain import Department, DepartmentTag, Role
from app.modules.system_admin.schemas.common import RoleName


def tag_item(tag: DepartmentTag) -> dict[str, str]:
    return {"id": str(tag.id), "name": tag.name}


def department_node(dept: Department, *, children: list[dict] | None = None) -> dict:
    tags = [tag_item(t) for t in sorted(dept.tags, key=lambda t: (t.name, t.id))]
    roles = [
        RoleName(id=str(role.id), name=role.name).model_dump()
        for role in sorted(dept.roles, key=lambda r: (r.name, r.id))
    ]
    return {
        "id": str(dept.id),
        "name": dept.name,
        "parent_id": None if dept.parent_id is None else str(dept.parent_id),
        "sort": dept.sort,
        "enabled": bool(dept.enabled),
        "tenant": dept.tenant,
        "created_at": beijing_iso(dept.created_date),
        "tags": tags,
        "roles": roles,
        "children": [] if children is None else children,
    }


def role_brief(role: Role, assigned: bool, assigned_at: datetime | None) -> dict:
    return {
        "id": str(role.id),
        "name": role.name,
        "assigned": assigned,
        "assigned_at": beijing_iso(assigned_at) if assigned_at is not None else None,
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
    pool = [d for d in pool if not d.is_deleted]

    by_id = {str(d.id): d for d in depts}
    children_of: dict[str | None, list[Department]] = {}
    for dept in depts:
        if dept.is_deleted:
            continue
        parent_key = None if dept.parent_id is None else str(dept.parent_id)
        children_of.setdefault(parent_key, []).append(dept)

    if department_id:
        needle_id = department_id.strip()
        target = by_id.get(needle_id)
        if target is None or target.is_deleted:
            return []
        keep: set[str] = {needle_id}
        stack = [needle_id]
        while stack:
            current = stack.pop()
            for child in children_of.get(current, []):
                child_id = str(child.id)
                if child_id not in keep:
                    keep.add(child_id)
                    stack.append(child_id)
        cursor = None if target.parent_id is None else str(target.parent_id)
        while cursor:
            keep.add(cursor)
            parent = by_id.get(cursor)
            cursor = None if parent is None or parent.parent_id is None else str(parent.parent_id)
        pool = [d for d in pool if str(d.id) in keep]

    if not name:
        return pool

    needle = name.casefold()
    by_parent: dict[str | None, list[Department]] = {}
    for dept in pool:
        parent_key = None if dept.parent_id is None else str(dept.parent_id)
        by_parent.setdefault(parent_key, []).append(dept)
    pool_ids = {str(d.id) for d in pool}

    def subtree_matches(dept: Department) -> bool:
        if needle in dept.name.casefold():
            return True
        for child in by_parent.get(str(dept.id), []):
            if str(child.id) in pool_ids and subtree_matches(child):
                return True
        return False

    return [d for d in pool if subtree_matches(d)]


def build_department_tree(depts: list[Department]) -> list[dict]:
    ids = {str(d.id) for d in depts}
    nodes = {str(d.id): department_node(d, children=[]) for d in depts}
    roots: list[dict] = []
    for dept in depts:
        node = nodes[str(dept.id)]
        parent_id = None if dept.parent_id is None else str(dept.parent_id)
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
