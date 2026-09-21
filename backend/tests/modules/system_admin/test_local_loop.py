from __future__ import annotations

import unittest

from app.modules.system_admin.deps import require_menu
from app.modules.system_admin.domain.access import MENU_DEPARTMENTS, MENU_USERS, build_menu_tree
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
    def __init__(self, id: str, name: str, parent_id: str | None = None, *, enabled: bool = True, deleted_at=None):
        self.id = id
        self.name = name
        self.parent_id = parent_id
        self.enabled = enabled
        self.deleted_at = deleted_at
        self.sort = 0
        self.tags = []
        self.roles = []


class DepartmentFilterTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tree = [
            _Dept("1", "投放部"),
            _Dept("2", "投放一部", "1"),
            _Dept("3", "素材部"),
            _Dept("4", "已删", deleted_at="x"),
        ]

    def test_exact_id_keeps_ancestors_and_children(self) -> None:
        got = {d.id for d in filter_departments(self.tree, None, None, "2")}
        self.assertEqual(got, {"1", "2"})

    def test_deleted_id_is_empty(self) -> None:
        self.assertEqual(filter_departments(self.tree, None, None, "4"), [])


if __name__ == "__main__":
    unittest.main()
