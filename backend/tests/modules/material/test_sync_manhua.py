"""漫剧落库去重与页签判断。"""

from __future__ import annotations

import unittest

from app.modules.material.service import collapse_by_playlet_book, fields_from_item, tab_text_from_price


class TabTextTests(unittest.TestCase):
    def test_free_price_is_iaa_and_charged_is_iap(self) -> None:
        """单价为空或 0 是 IAA，大于 0 是 IAP。"""
        self.assertEqual(tab_text_from_price(""), "IAA")
        self.assertEqual(tab_text_from_price(None), "IAA")
        self.assertEqual(tab_text_from_price("0"), "IAA")
        self.assertEqual(tab_text_from_price("0.00"), "IAA")
        self.assertEqual(tab_text_from_price("200"), "IAP")


class CollapseTests(unittest.TestCase):
    def test_same_playlet_and_name_keeps_the_later_row(self) -> None:
        """同一专辑 ID 和剧名只留最后一条，没有剧名的丢掉。"""
        rows = collapse_by_playlet_book(
            [
                {"playlet_id": 9, "book_name": "同名", "single_price": "0"},
                {"playlet_id": 9, "book_name": "同名", "single_price": "50"},
                {"playlet_id": 9, "single_price": "10"},
            ]
        )
        self.assertEqual(set(rows), {(9, "同名")})
        self.assertEqual(rows[(9, "同名")]["tab_text"], "IAP")

    def test_category_text_stays_genre_and_tab_comes_from_price(self) -> None:
        """常读题材进 category_text，不写进页签。"""
        fields = fields_from_item(
            {"book_id": 1, "category_text": "玄幻脑洞,逆袭", "single_price": "0"}
        )
        self.assertEqual(fields["category_text"], "玄幻脑洞,逆袭")
        self.assertEqual(fields["tab_text"], "IAA")
