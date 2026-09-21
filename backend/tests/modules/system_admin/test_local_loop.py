from __future__ import annotations

import unittest

from app.core.envelope import ApiError
from app.modules.system_admin.deps import require_menu
from app.modules.system_admin.domain.access import MENU_DEPARTMENTS, MENU_USERS, build_menu_tree
from app.modules.system_admin.domain.ids import parse_int_id, require_int_id
from app.modules.system_admin.domain.seed_data import (
    LOCAL_DEPARTMENTS,
    local_user_role_seed_rows,
    local_user_seed_rows,
    role_menu_seed_rows,
)
from app.modules.system_admin.domain.tags import (
    DEPARTMENT_TAG_NAMES,
    require_department_tag_name,
    require_user_tag_name,
)
from app.modules.system_admin.schemas.departments import filter_departments


class LocalMockSeedTests(unittest.TestCase):
    def test_admin_and_pitcher_seeded(self) -> None:
        accounts = {row["login_account"] for row in local_user_seed_rows()}
        self.assertEqual(accounts, {"admin", "disabled", "pitcher"})
        self.assertEqual({row["id"] for row in LOCAL_DEPARTMENTS}, {1, 2})

    def test_admin_has_ops_role(self) -> None:
        pairs = {(row["user_id"], row["role_id"]) for row in local_user_role_seed_rows()}
        self.assertIn((1, 5), pairs)
        self.assertIn((3, 6), pairs)

    def test_ops_role_has_system_admin_menus(self) -> None:
        granted = {row["menu_id"] for row in role_menu_seed_rows() if row["role_id"] == 5}
        self.assertTrue({98, 100, 101, 102} <= granted)


class MenuTreeTests(unittest.TestCase):
    def test_empty_grant_is_empty_tree(self) -> None:
        self.assertEqual(build_menu_tree({}, set()), [])

    def test_require_menu_needs_ids(self) -> None:
        with self.assertRaises(ValueError):
            require_menu()
        self.assertTrue(callable(require_menu(MENU_DEPARTMENTS, MENU_USERS)))


class TagCatalogTests(unittest.TestCase):
    def test_department_tags_are_closed(self) -> None:
        self.assertEqual(DEPARTMENT_TAG_NAMES, ("投放部", "投放组", "素材部", "素材组"))
        self.assertEqual(require_department_tag_name(" 投放部 "), "投放部")
        with self.assertRaises(ValueError):
            require_department_tag_name("财务部")

    def test_user_tags_are_closed(self) -> None:
        self.assertEqual(require_user_tag_name("投手"), "投手")
        with self.assertRaises(ValueError):
            require_user_tag_name("运营")


class _Dept:
    def __init__(self, id: str, name: str, parent_id: str | None = None, *, enabled: bool = True, is_deleted: int = 0):
        self.id = id
        self.name = name
        self.parent_id = parent_id
        self.enabled = enabled
        self.is_deleted = is_deleted
        self.sort = 0
        self.tags = []
        self.roles = []


class DepartmentFilterTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tree = [
            _Dept("1", "投放部"),
            _Dept("2", "投放一部", "1"),
            _Dept("3", "素材部"),
            _Dept("4", "已删", is_deleted=1),
        ]

    def test_exact_id_keeps_ancestors_and_children(self) -> None:
        got = {d.id for d in filter_departments(self.tree, None, None, "2")}
        self.assertEqual(got, {"1", "2"})

    def test_deleted_id_is_empty(self) -> None:
        self.assertEqual(filter_departments(self.tree, None, None, "4"), [])


class IntIdTests(unittest.TestCase):
    def test_parse_accepts_positive_decimal(self) -> None:
        self.assertEqual(parse_int_id("12"), "12")
        self.assertEqual(parse_int_id(7), "7")

    def test_parse_rejects_junk(self) -> None:
        self.assertIsNone(parse_int_id("abc"))
        self.assertIsNone(parse_int_id("01"))
        self.assertIsNone(parse_int_id("0"))
        self.assertIsNone(parse_int_id(True))

    def test_require_int_id_returns_int(self) -> None:
        self.assertEqual(require_int_id("12", "用户不存在"), 12)
        self.assertEqual(require_int_id(7, "用户不存在"), 7)

    def test_require_int_id_is_not_found(self) -> None:
        with self.assertRaises(ApiError) as ctx:
            require_int_id("abc", "用户不存在")
        self.assertEqual(ctx.exception.status_code, 404)
        self.assertEqual(ctx.exception.code, "NOT_FOUND")


if __name__ == "__main__":
    unittest.main()
