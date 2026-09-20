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


class LocalMockSeedTests(unittest.TestCase):
    def test_admin_and_pitcher_seeded(self) -> None:
        accounts = {row["login_account"] for row in local_user_seed_rows()}
        self.assertEqual(accounts, {"admin", "disabled", "pitcher"})
        self.assertEqual({row["id"] for row in LOCAL_DEPARTMENTS}, {"1", "2"})

    def test_admin_has_ops_role(self) -> None:
        pairs = {(row["user_id"], row["role_id"]) for row in local_user_role_seed_rows()}
        self.assertIn(("1", "5"), pairs)
        self.assertIn(("3", "6"), pairs)

    def test_ops_role_has_system_admin_menus(self) -> None:
        granted = {row["menu_id"] for row in role_menu_seed_rows() if row["role_id"] == "5"}
        self.assertTrue({"98", "100", "101", "102"} <= granted)


class MenuTreeTests(unittest.TestCase):
    def test_empty_grant_is_empty_tree(self) -> None:
        self.assertEqual(build_menu_tree({}, set()), [])

    def test_require_menu_needs_ids(self) -> None:
        with self.assertRaises(ValueError):
            require_menu()
        self.assertTrue(callable(require_menu(MENU_DEPARTMENTS, MENU_USERS)))


if __name__ == "__main__":
    unittest.main()
