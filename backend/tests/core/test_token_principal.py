from __future__ import annotations

import json
import unittest

from app.core.auth import parse_principal


class ParsePrincipalTests(unittest.TestCase):
    def test_keeps_menu_ids_as_list(self) -> None:
        raw = json.dumps(
            {
                "id": "1",
                "nickname": "管理员",
                "login_account": "admin",
                "tenant": "ops",
                "enabled": True,
                "menu_ids": ["98", "101"],
            }
        )
        principal = parse_principal(raw)
        assert principal is not None
        self.assertEqual(principal["login_account"], "admin")
        self.assertEqual(principal["enabled"], True)
        self.assertEqual(principal["menu_ids"], ["98", "101"])

    def test_old_payload_without_acl_still_parses(self) -> None:
        raw = json.dumps(
            {
                "id": "1",
                "nickname": "管理员",
                "login_account": "admin",
                "tenant": "ops",
            }
        )
        principal = parse_principal(raw)
        assert principal is not None
        self.assertNotIn("menu_ids", principal)
        self.assertNotIn("enabled", principal)

    def test_rejects_garbage(self) -> None:
        self.assertIsNone(parse_principal("not-json"))
        self.assertIsNone(parse_principal("[]"))
        self.assertIsNone(parse_principal("{}"))


if __name__ == "__main__":
    unittest.main()
