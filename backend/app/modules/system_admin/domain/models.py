from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Identity,
    Integer,
    String,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.modules.system_admin.domain.base import Base
from app.modules.system_admin.domain.enums import (
    MENU_TYPE_COMPONENT,
    MENU_TYPE_DIRECTORY,
    MENU_TYPE_MENU,
    ROLE_KIND_MEMBER,
    ROLE_KIND_OWNER,
)

_PK = Integer()
_TS = DateTime(timezone=True)


class Department(Base):
    __tablename__ = "departments"

    id: Mapped[int] = mapped_column(_PK, Identity(), primary_key=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    parent_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("departments.id", ondelete="RESTRICT"), nullable=True
    )
    sort: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"))
    tenant: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(_TS, nullable=False, server_default=func.now())
    deleted_at: Mapped[datetime | None] = mapped_column(_TS, nullable=True)

    parent: Mapped[Department | None] = relationship(
        remote_side="Department.id", back_populates="children"
    )
    children: Mapped[list[Department]] = relationship(back_populates="parent")
    tags: Mapped[list[DepartmentTag]] = relationship(
        secondary="department_tag_links", back_populates="departments"
    )
    users: Mapped[list[User]] = relationship(back_populates="department")
    roles: Mapped[list[Role]] = relationship(
        "Role", secondary="department_roles", viewonly=True
    )


class DepartmentTag(Base):
    __tablename__ = "department_tags"

    id: Mapped[int] = mapped_column(_PK, Identity(), primary_key=True)
    name: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    created_at: Mapped[datetime] = mapped_column(_TS, nullable=False, server_default=func.now())

    departments: Mapped[list[Department]] = relationship(
        secondary="department_tag_links", back_populates="tags"
    )


class DepartmentTagLink(Base):
    __tablename__ = "department_tag_links"
    __table_args__ = (UniqueConstraint("department_id", "tag_id", name="uq_department_tag"),)

    department_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("departments.id", ondelete="CASCADE"), primary_key=True
    )
    tag_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("department_tags.id", ondelete="CASCADE"), primary_key=True
    )


class Role(Base):
    __tablename__ = "roles"

    id: Mapped[int] = mapped_column(_PK, Identity(), primary_key=True)
    name: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    remark: Mapped[str | None] = mapped_column(String(200), nullable=True)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"))
    created_at: Mapped[datetime] = mapped_column(_TS, nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        _TS, nullable=False, server_default=func.now(), onupdate=func.now()
    )
    updated_by: Mapped[str | None] = mapped_column(String(64), nullable=True)

    menus: Mapped[list[MenuNode]] = relationship(secondary="role_menus", back_populates="roles")


class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint(
            f"role_kind IN ('{ROLE_KIND_OWNER}', '{ROLE_KIND_MEMBER}')",
            name="ck_users_role_kind",
        ),
    )

    id: Mapped[int] = mapped_column(_PK, Identity(), primary_key=True)
    nickname: Mapped[str] = mapped_column(String(64), nullable=False)
    login_account: Mapped[str] = mapped_column(
        String(64), nullable=False, unique=True, comment="创建后不可改"
    )
    short_name: Mapped[str | None] = mapped_column(String(64), nullable=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    phone: Mapped[str | None] = mapped_column(String(32), nullable=True)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"))
    department_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("departments.id", ondelete="RESTRICT"), nullable=False
    )
    role_kind: Mapped[str] = mapped_column(
        String(16), nullable=False, server_default=text(f"'{ROLE_KIND_MEMBER}'")
    )
    remark: Mapped[str | None] = mapped_column(String(200), nullable=True)
    tenant: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(_TS, nullable=False, server_default=func.now())
    deleted_at: Mapped[datetime | None] = mapped_column(_TS, nullable=True)

    department: Mapped[Department] = relationship(back_populates="users")
    tags: Mapped[list[UserTag]] = relationship(secondary="user_tag_links", back_populates="users")
    roles: Mapped[list[Role]] = relationship(secondary="user_roles")
    data_scope_departments: Mapped[list[Department]] = relationship(secondary="user_data_scopes")


class UserTag(Base):
    __tablename__ = "user_tags"

    id: Mapped[int] = mapped_column(_PK, Identity(), primary_key=True)
    name: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    created_at: Mapped[datetime] = mapped_column(_TS, nullable=False, server_default=func.now())

    users: Mapped[list[User]] = relationship(secondary="user_tag_links", back_populates="tags")


class UserTagLink(Base):
    __tablename__ = "user_tag_links"
    __table_args__ = (UniqueConstraint("user_id", "tag_id", name="uq_user_tag"),)

    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    tag_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("user_tags.id", ondelete="CASCADE"), primary_key=True
    )


class MenuNode(Base):
    __tablename__ = "menu_nodes"
    __table_args__ = (
        CheckConstraint(
            f"type IN ('{MENU_TYPE_DIRECTORY}', '{MENU_TYPE_MENU}', '{MENU_TYPE_COMPONENT}')",
            name="ck_menu_nodes_type",
        ),
    )

    id: Mapped[int] = mapped_column(_PK, Identity(), primary_key=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    type: Mapped[str] = mapped_column(String(16), nullable=False)
    parent_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("menu_nodes.id", ondelete="RESTRICT"), nullable=True
    )
    business_domain: Mapped[str | None] = mapped_column(String(64), nullable=True)
    tenant_kind: Mapped[str | None] = mapped_column(String(64), nullable=True)

    parent: Mapped[MenuNode | None] = relationship(
        remote_side="MenuNode.id", back_populates="children"
    )
    children: Mapped[list[MenuNode]] = relationship(back_populates="parent")
    roles: Mapped[list[Role]] = relationship(secondary="role_menus", back_populates="menus")


class DepartmentRole(Base):
    __tablename__ = "department_roles"
    __table_args__ = (UniqueConstraint("department_id", "role_id", name="uq_department_role"),)

    department_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("departments.id", ondelete="CASCADE"), primary_key=True
    )
    role_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True
    )
    assigned_at: Mapped[datetime] = mapped_column(_TS, nullable=False, server_default=func.now())


class UserRole(Base):
    __tablename__ = "user_roles"
    __table_args__ = (UniqueConstraint("user_id", "role_id", name="uq_user_role"),)

    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    role_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True
    )
    assigned_at: Mapped[datetime] = mapped_column(_TS, nullable=False, server_default=func.now())


class UserDataScope(Base):
    __tablename__ = "user_data_scopes"
    __table_args__ = (UniqueConstraint("user_id", "department_id", name="uq_user_data_scope"),)

    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    department_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("departments.id", ondelete="CASCADE"), primary_key=True
    )


class RoleMenu(Base):
    __tablename__ = "role_menus"
    __table_args__ = (UniqueConstraint("role_id", "menu_id", name="uq_role_menu"),)

    role_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True
    )
    menu_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("menu_nodes.id", ondelete="CASCADE"), primary_key=True
    )


class DictItem(Base):
    """字典配置。至少承载默认密码（Q-PERM-5），不写死 135。"""

    __tablename__ = "dict_items"

    id: Mapped[int] = mapped_column(_PK, Identity(), primary_key=True)
    dict_code: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    value: Mapped[str] = mapped_column(String(255), nullable=False)
    remark: Mapped[str | None] = mapped_column(String(200), nullable=True)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"))
    created_at: Mapped[datetime] = mapped_column(_TS, nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        _TS, nullable=False, server_default=func.now(), onupdate=func.now()
    )
