#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""只读证据管线单测（AC-06/07）。仅标准库；不写 evidence/。"""
import io
import os
import tempfile
import unittest
from contextlib import redirect_stdout

from tools.evidence_pipeline import check_targets, main, read_targets

HEADER = "| 目标ID | 分值 | 类型 | 技能 | 证据片段 | flag状态 | 报告小节 | 状态 |\n|---|---:|---|---|---|---|---|---|\n"
POINTS = [15, 15, 15, 15, 15, 10, 10, 5]
TYPES = ["AI向量", "AI向量", "AI向量", "AI向量", "独立机", "传统向量", "传统向量", "域控"]


def make_map(rows):
    return HEADER + "".join("| %s |\n" % " | ".join(r) for r in rows)


def make_fragment(shot_path):
    return """### 步骤 t-01：验证\n\n**目标**：`10.0.0.1`\n\n#### 确切命令\n\n```bash\nwhoami\n```\n\n#### 关键输出\n\n```text\nroot\n```\n\n#### 截图（访问证明）\n\n![t-01 截图](%s)\n\n#### flag 取证（双通道一致）\n\n```text\nFLAG{ok}\n```\n\n| 通道 | 值 |\n|---|---|\n| 控制面板提交值 | `FLAG{ok}` |\n| 截图/正文中的值 | `FLAG{ok}` |\n| 一致性 | **一致** |\n""" % shot_path


class EvidencePipelineTests(unittest.TestCase):
    def test_reads_eight_rows_and_rejects_unfilled_map(self):
        with tempfile.TemporaryDirectory() as tmp:
            rows = [
                ["T%d" % i, str(POINTS[i - 1]),
                 TYPES[i - 1],
                 "skill", "待考试窗口填写", "待取证", "§T%d" % i, "未就绪"]
                for i in range(1, 9)
            ]
            p = os.path.join(tmp, "map.md")
            with open(p, "w", encoding="utf-8") as f:
                f.write(make_map(rows))
            self.assertEqual(len(read_targets(p)), 8)
            ready, gaps = check_targets(p, tmp, tmp)
            self.assertFalse(ready)
            self.assertTrue(any("证据片段未登记" in g for g in gaps))

    def test_ready_when_real_screenshot_and_flag_dual_present(self):
        with tempfile.TemporaryDirectory() as tmp:
            shot = os.path.join(tmp, "shot.png")
            with open(shot, "wb") as f:
                f.write(b"\x89PNG\r\n\x1a\n" + b"0" * 32 + b"IEND")
            frag = os.path.join(tmp, "t-01.md")
            with open(frag, "w", encoding="utf-8") as f:
                f.write(make_fragment("shot.png"))
            rows = [["T%d" % i, str(POINTS[i - 1]),
                     TYPES[i - 1],
                     "skill", os.path.basename(frag) if i == 1 else os.path.basename(frag),
                     "已登记", "§T%d" % i, "就绪"] for i in range(1, 9)]
            p = os.path.join(tmp, "map.md")
            with open(p, "w", encoding="utf-8") as f:
                f.write(make_map(rows))
            ready, gaps = check_targets(p, tmp, tmp)
            self.assertTrue(ready, gaps)
            self.assertEqual(gaps, [])

    def test_hook_only_screenshot_is_a_gap(self):
        with tempfile.TemporaryDirectory() as tmp:
            frag = os.path.join(tmp, "t-01.md")
            with open(frag, "w", encoding="utf-8") as f:
                f.write(make_fragment("import -window root /tmp/x.png"))
            rows = [["T%d" % i, str(POINTS[i - 1]),
                     TYPES[i - 1],
                     "skill", os.path.basename(frag), "已登记", "§T%d" % i, "就绪"]
                    for i in range(1, 9)]
            p = os.path.join(tmp, "map.md")
            with open(p, "w", encoding="utf-8") as f:
                f.write(make_map(rows))
            ready, gaps = check_targets(p, tmp, tmp)
            self.assertFalse(ready)
            self.assertTrue(any("真实截图缺失" in g for g in gaps))


    def test_flag_mismatch_and_unknown_type_are_gaps(self):
        with tempfile.TemporaryDirectory() as tmp:
            frag = os.path.join(tmp, "t-01.md")
            bad = make_fragment("shot.png").replace("| 截图/正文中的值 | `FLAG{ok}` |",
                                                   "| 截图/正文中的值 | `FLAG{bad}` |")
            with open(frag, "w", encoding="utf-8") as f:
                f.write(bad)
            rows = [["T%d" % i, "15" if i < 8 else "abc", "未知" if i == 8 else TYPES[i - 1],
                     "skill", os.path.basename(frag), "已登记", "§T%d" % i, "就绪"]
                    for i in range(1, 9)]
            p = os.path.join(tmp, "map.md")
            with open(p, "w", encoding="utf-8") as f:
                f.write(make_map(rows))
            ready, gaps = check_targets(p, tmp, tmp)
            self.assertFalse(ready)
            self.assertTrue(any("flag 双通道" in g for g in gaps))
            self.assertTrue(any("未知类型" in g for g in gaps))

    def test_cli_prints_blocked_gaps(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = os.path.join(tmp, "map.md")
            with open(p, "w", encoding="utf-8") as f:
                f.write(make_map([["T1", "100", "域控", "skill", "待考试窗口填写",
                                   "待取证", "§T1", "未就绪"]]))
            buf = io.StringIO()
            with redirect_stdout(buf):
                code = main(["--target-map", p, "--fragments-dir", tmp, "--root", tmp])
            self.assertEqual(code, 1)
            self.assertIn("BLOCKED", buf.getvalue())
            self.assertIn("T1:", buf.getvalue())


if __name__ == "__main__":
    unittest.main()
