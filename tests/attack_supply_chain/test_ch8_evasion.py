# -*- coding: utf-8 -*-
"""阶段9 TDD：G9 隐身后门 + G10 八类登记（编解码往返 / 清单完整）。"""
import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)

from tools.attack_supply_chain.stealth_backdoor import (anti_sandbox_checks,
                                                        blue_team_detection,
                                                        from_zero_width, to_zero_width,
                                                        xor_transform)
from tools.attack_supply_chain.ch8_evasion import all_techniques


class TestStealthBackdoor(unittest.TestCase):
    def test_xor_roundtrip(self):
        data = b"hello world"
        self.assertEqual(xor_transform(xor_transform(data)), data)

    def test_zero_width_roundtrip(self):
        text = "import sys; print('x')"
        zw = to_zero_width(text)
        self.assertEqual(len(zw), len(text.encode("utf-8")) * 8)
        self.assertEqual(from_zero_width(zw), text)

    def test_zero_width_chars(self):
        zw = to_zero_width("A")
        self.assertTrue(set(zw) <= {"\u200b", "\u200c"})

    def test_anti_sandbox_six(self):
        self.assertEqual(len(anti_sandbox_checks()), 6)

    def test_blue_team_four(self):
        self.assertEqual(len(blue_team_detection()), 4)


class TestEvasionRegistry(unittest.TestCase):
    def test_eight_techniques(self):
        rows = all_techniques()
        self.assertEqual(len(rows), 8)
        self.assertTrue(all(r.status == "文档列出但未实现" for r in rows))


if __name__ == "__main__":
    unittest.main()
