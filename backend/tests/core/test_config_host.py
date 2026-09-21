from __future__ import annotations

import unittest

from app.core.config import _host_for_this_process, get_settings


class ComposeHostFallbackTests(unittest.TestCase):
    def test_literal_ip_is_unchanged(self) -> None:
        self.assertEqual(_host_for_this_process("192.168.112.12"), "192.168.112.12")
        self.assertEqual(_host_for_this_process("127.0.0.1"), "127.0.0.1")

    def test_compose_service_name_is_usable_here(self) -> None:
        host = _host_for_this_process("postgres")
        self.assertIn(host, {"postgres", "127.0.0.1"})

    def test_dev_settings_reach_mapped_ports(self) -> None:
        get_settings.cache_clear()
        settings = get_settings()
        self.assertIn(settings.postgres.host, {"postgres", "127.0.0.1"})
        self.assertIn(settings.redis.host, {"redis", "127.0.0.1"})
        self.assertEqual(settings.postgres.port, 5432)
        self.assertEqual(settings.redis.port, 6379)
        self.assertGreaterEqual(len(settings.jwt_secret), 32)
