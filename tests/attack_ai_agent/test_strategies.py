#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""策略库读取、筛选与聚合的单元测试（方案 P5）。

约束：策略库是数据文件，测试必须验证「数据完整性」而非「文案好看」——
每条策略都要有可编译的判据正则，否则运行期才发现会破坏一次实跑。
"""
import json
import os
import re
import tempfile
import unittest

from tools.attack_ai_agent import strategies


class LoadTest(unittest.TestCase):
    def test_default_library_loads(self):
        library = strategies.load()
        self.assertGreaterEqual(len(library), 7)
        ids = {s.id for s in library}
        for expected in ("S-ANCHOR", "S-VERBATIM", "S-SYS-NOTICE", "S-CONTEXT-PAD"):
            self.assertIn(expected, ids)

    def test_all_patterns_compile(self):
        for item in strategies.load():
            with self.subTest(strategy=item.id):
                re.compile(item.pattern)
                self.assertTrue(item.steps, "策略缺载荷步骤")

    def test_status_values_are_known(self):
        for item in strategies.load():
            self.assertIn(item.status,
                          ("proven", "unstable", "refuted", "unproven"))

    def test_missing_file_returns_empty(self):
        self.assertEqual(strategies.load(os.path.join(tempfile.gettempdir(),
                                                      "__no_such_lib__.json")), [])

    def test_invalid_entry_raises(self):
        handle = tempfile.NamedTemporaryFile(
            "w", suffix=".json", delete=False, encoding="utf-8")
        json.dump({"strategies": [{"id": "X", "steps": ["a"]}]}, handle)
        handle.close()
        try:
            with self.assertRaises(ValueError):
                strategies.load(handle.name)
        finally:
            os.unlink(handle.name)


class SelectTest(unittest.TestCase):
    def test_select_by_id_is_case_insensitive(self):
        selected = strategies.select(strategies.load(), ["s-anchor"])
        self.assertEqual([s.id for s in selected], ["S-ANCHOR"])

    def test_select_by_status(self):
        proven = strategies.select(strategies.load(), status="proven")
        refuted = strategies.select(strategies.load(), status="refuted")
        self.assertTrue(proven)
        self.assertTrue(refuted)
        self.assertFalse({s.id for s in proven} & {s.id for s in refuted})

    def test_empty_selection(self):
        self.assertEqual(strategies.select(strategies.load(), ["NOPE"]), [])


class AggregateTest(unittest.TestCase):
    def test_rate(self):
        rows = [{"strategy_id": "S", "effective": True},
                {"strategy_id": "S", "effective": False},
                {"strategy_id": "S", "effective": True}]
        result = strategies.aggregate(rows)
        self.assertEqual(result["S"]["attempts"], 3)
        self.assertEqual(result["S"]["effective"], 2)
        self.assertAlmostEqual(result["S"]["rate"], 0.667, places=3)

    def test_rows_without_id_ignored(self):
        self.assertEqual(strategies.aggregate([{"effective": True}]), {})


class RenderTest(unittest.TestCase):
    def test_table_has_header_and_all_rows(self):
        library = strategies.load()
        text = strategies.render_table(library)
        self.assertIn("ID", text.splitlines()[0])
        for item in library:
            self.assertIn(item.id, text)


if __name__ == "__main__":
    unittest.main()
