#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""C4 预算：阶段门禁记录必须 ≤2,000 字节。

计数口径与 `scripts/check_token_budget.py` 一致——按 LF 归一化后的 UTF-8 字节。
不要用 `wc -c` / `find -size` 直接测工作树：Windows 上 `core.autocrlf=true` 会给每行
多记 1 字节，`capstone-rehearse-gate-stage11.md` 因此被误判为 2,021B 超限（实为 1,997B），
进而触发过一次无谓的记录改写。
"""
import unittest

from tests._paths import ROOT_PATH  # noqa: E402

LIMIT = 2000


def _normalized_size(path):
    text = path.read_text(encoding="utf-8").replace("\r\n", "\n")
    return len(text.encode("utf-8"))


class GateRecordBudgetTests(unittest.TestCase):
    """`docs/operations/*-gate-stage*.md` 全部纳入 C4 预算判定。"""

    def test_gate_records_within_budget(self):
        records = sorted((ROOT_PATH / "docs" / "operations").glob("*-gate-stage*.md"))
        self.assertTrue(records, "未找到任何阶段门禁记录，路径约定可能已变更")
        over = ["%s: %d" % (p.name, _normalized_size(p))
                for p in records if _normalized_size(p) > LIMIT]
        self.assertEqual(over, [], "超 C4 预算（%d 字节，LF 口径）：%s" % (LIMIT, "；".join(over)))


if __name__ == "__main__":
    unittest.main()
