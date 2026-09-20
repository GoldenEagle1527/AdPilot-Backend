from __future__ import annotations

from datetime import datetime, timezone

from pydantic import BaseModel, ConfigDict, Field

from app.modules.system_admin.domain import Department, DepartmentTag, Role


def iso_z(dt: datetime) -> str:
    if dt.tzinfo is None:
        aware = dt.replace(tzinfo=timezone.utc)
    else:
        aware = dt.astimezone(timezone.utc)
    return aware.isoformat().replace("+00:00", "Z")


def tag_item(tag: DepartmentTag) -> dict[str, str]:
    return {"id": tag.id, "name": tag.name}


def department_node(dept: Department, *, children: list[dict] | None = None) -> dict:
    tags = [tag_item(t) for t in sorted(dept.tags, key=lambda t: (t.name, t.id))]
    return {
        "id": dept.id,
        "name": dept.name,
        "parent_id": dept.parent_id,
        "sort": dept.sort,
        "enabled": bool(dept.enabled),
        "tenant": dept.tenant,
        "created_at": iso_z(dept.created_at),
        "tags": tags,
        "children": [] if children is None else children,
    }


def role_brief(role: Role, assigned: bool, assigned_at: datetime | None) -> dict:
    return {
        "id": role.id,
        "name": role.name,
        "assigned": assigned,
        "assigned_at": iso_z(assigned_at) if assigned_at is not None else None,
    }


def filter_departments(
    depts: list[Department],
    name: str | None,
    enabled: bool | None,
) -> list[Department]:
    if enabled is not None:
        pool = [d for d in depts if d.enabled == enabled]
    else:
        pool = list(depts)
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


class SetDepartmentRolesBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    role_ids: list[str]
