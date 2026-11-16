#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""capstone-rehearse 证据契约夹具（B4 / AC-21）。

断言每步经共享 `collect_evidence.py --strict` 产出的片段含三件套
（确切命令 / 关键输出 / 截图）与 AI 交互日志；本技能不取 flag，
双通道保持「未提供」而非伪造。仅标准库 unittest。
"""
import os
import sys
import tempfile
import unittest

from tests._paths import ROOT  # noqa: E402
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from tools.capstone_rehearse.evidence import STEPS, EvidenceWriter  # noqa: E402


class EvidenceContractTests(unittest.TestCase):
    def test_writer_delegates_shared_collector(self):
        self.assertIn("collect_evidence.py", EvidenceWriter("/tmp/unused").describe())

    def test_six_drill_steps_defined(self):
        self.assertEqual(tuple(s[0] for s in STEPS),
                         ("cr-01", "cr-02", "cr-03", "cr-04", "cr-05", "cr-06"))

    def test_emit_produces_three_piece_and_ai_log(self):
        with tempfile.TemporaryDirectory() as tmp:
            out_dir = os.path.join(tmp, "drill")
            writer = EvidenceWriter(out_dir)
            path, code, err = writer.emit(
                "cr-01",
                "python -m tools.capstone_rehearse --stdout --step cr-01",
                "cr-01 覆盖度矩阵: 9 行, 就绪 0",
                "九阶段覆盖度矩阵",
                "edge --headless=new --screenshot=cr-01.png <演练面板>")
            self.assertEqual(code, 0, err)
            with open(path, encoding="utf-8") as handle:
                text = handle.read()
            for heading in ("#### 确切命令", "#### 关键输出", "#### 截图",
                            "#### AI 交互日志"):
                self.assertIn(heading, text)
            self.assertIn("三件套齐全**：是", text)

    def test_no_fabricated_flag_dual_channel(self):
        with tempfile.TemporaryDirectory() as tmp:
            writer = EvidenceWriter(os.path.join(tmp, "drill"))
            path, code, _ = writer.emit(
                "cr-06", "python -m tools.capstone_rehearse --stdout --step cr-06",
                "cr-06 机读结果", "机读结果与退出码", "shot-cmd")
            self.assertEqual(code, 0)
            with open(path, encoding="utf-8") as handle:
                text = handle.read()
            self.assertIn("| flag 双通道 | 否 | 未提供 |", text)


if __name__ == "__main__":
    unittest.main()
