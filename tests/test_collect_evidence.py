#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""证据收集工具自测（S2）。

以假数据调用 tools/collect_evidence.py，断言其产出的 markdown 片段满足质量门：
  1. 含「三件套」（确切命令 / 关键输出 / 截图）各小节；
  2. 命令可被技术读者 copy/paste 复现（出现在 ```bash 围栏内）；
  3. 三件套齐全性校验正确（齐全/缺失判定、--strict 强制失败）；
  4. 输入含 GLOSSARY.md `_Avoid_` 废弃术语时给出预警。

仅依赖标准库（unittest），与 test_validators.py 同一 subprocess 约定。
运行：python -m unittest discover -s tests
"""
import os
import subprocess
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOL = os.path.join(ROOT, "tools", "collect_evidence.py")


def run(*args):
    return subprocess.run(
        [sys.executable, TOOL] + list(args),
        cwd=ROOT, capture_output=True, text=True,
    )


class CollectEvidenceTests(unittest.TestCase):
    def test_cli_produces_complete_fragment(self):
        with tempfile.TemporaryDirectory() as tmp:
            shot = os.path.join(tmp, "recon-01.png")
            with open(shot, "wb") as f:
                f.write(b"\x89PNG\r\n\x1a\n")  # 假 PNG 头，仅用于文件存在性
            out = os.path.join(tmp, "out.md")
            r = run(
                "--step", "recon-01",
                "--cmd", "nmap -sC -sV -p- 10.0.0.5",
                "--output", "22/tcp open ssh",
                "--screenshot", shot,
                "--target", "10.0.0.5",
                "--out", out,
            )
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            with open(out, encoding="utf-8") as f:
                text = f.read()
            for label in ("确切命令", "关键输出", "截图（访问证明）"):
                self.assertIn(label, text)
            self.assertIn("nmap -sC -sV -p- 10.0.0.5", text)
            self.assertIn("22/tcp open ssh", text)
            self.assertIn("```bash", text)  # copy/paste 可复现
            self.assertIn("**三件套齐全**：是。", text)

    def test_acceptance_minimal_still_runs_and_flags_incomplete(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = os.path.join(tmp, "out.md")
            # 验收命令只给 --step --cmd --out，缺输出与截图，仍应成功产出并标注缺失
            r = run("--step", "recon-01", "--cmd", "whoami", "--out", out)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            with open(out, encoding="utf-8") as f:
                text = f.read()
            self.assertIn("whoami", text)
            self.assertIn("**三件套齐全**：否（缺失：关键输出、截图）。", text)

    def test_strict_fails_when_incomplete(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = os.path.join(tmp, "out.md")
            r = run("--step", "s1", "--cmd", "id", "--out", out, "--strict")
            self.assertEqual(r.returncode, 1)
            self.assertIn("三件套不全", r.stdout + r.stderr)

    def test_warns_on_avoid_term(self):
        with tempfile.TemporaryDirectory() as tmp:
            glossary = os.path.join(tmp, "GLOSSARY.md")
            with open(glossary, "w", encoding="utf-8") as f:
                f.write("**诱饵机**:\n计分外主机。\n_Avoid_: 蜜罐、rabbit hole\n")
            out = os.path.join(tmp, "out.md")
            r = run("--step", "s1", "--cmd", "echo 扫描蜜罐主机", "--out", out,
                    "--glossary", glossary)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            self.assertIn("蜜罐", r.stderr)


if __name__ == "__main__":
    unittest.main()
