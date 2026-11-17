#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""decoy-detect 证据契约夹具（S2）。

把 SKILL.md 质量门的「每步命令 + 输出 + 截图」语义从人工复核升级为机器强制：
断言证据 seam（`tools/decoy_detect/evidence.py`）委托共享 `collect_evidence.py`，
产出的片段含三件套（确切命令 / 关键输出 / 截图）且判定为「三件套齐全」。

仅依赖标准库（unittest），与 tests/shared_tools/test_collect_evidence.py 同一 subprocess 约定。
运行：python -m unittest discover -s tests -t .
"""
import os
import sys
import tempfile
import unittest

from tests._paths import ROOT  # noqa: E402
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from tools.decoy_detect.evidence import EvidenceWriter  # noqa: E402


class DecoyEvidenceContractTests(unittest.TestCase):
    def test_writer_delegates_shared_collector(self):
        writer = EvidenceWriter("/tmp/unused")
        self.assertIn("collect_evidence.py", writer.describe())

    def test_fragment_path(self):
        writer = EvidenceWriter("/tmp/decoy-ev")
        self.assertTrue(writer.fragment_path("decoy-01").endswith("decoy-01.md"))

    def test_emit_produces_three_piece(self):
        with tempfile.TemporaryDirectory() as d:
            shot = os.path.join(d, "shot.png")
            with open(shot, "wb") as f:
                f.write(b"\x89PNG\r\n\x1a\n")
            writer = EvidenceWriter(os.path.join(d, "ev"))
            path, code, err = writer.emit(
                "decoy-01",
                "python tools/decoy_detect/cli.py run --inventory tests/fixtures/decoy_scan.json",
                "host=10.10.10.5\nhits=行为特征、漏洞缺失\nconclusion=诱饵",
                target="10.10.10.5", title="诱饵判定：10.10.10.5",
                screenshot=shot, shot_kind="transcript", strict=True)
            self.assertEqual(code, 0, err)
            with open(path, encoding="utf-8") as f:
                text = f.read()
            self.assertIn("#### 确切命令", text)
            self.assertIn("#### 关键输出", text)
            self.assertIn("#### 截图", text)
            self.assertIn("三件套齐全**：是", text)

    def test_emit_nonstrict_without_screenshot(self):
        with tempfile.TemporaryDirectory() as d:
            writer = EvidenceWriter(os.path.join(d, "ev"))
            path, code, _err = writer.emit(
                "decoy-02", "python tools/decoy_detect/cli.py run --inventory x",
                "host=h\nconclusion=不确定-已放弃", target="h2", strict=False)
            self.assertEqual(code, 0)
            with open(path, encoding="utf-8") as f:
                self.assertIn("三件套齐全**：否", f.read())


if __name__ == "__main__":
    unittest.main()
