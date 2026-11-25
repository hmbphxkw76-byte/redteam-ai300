#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""证据收集工具自测（S2）。

以假数据调用 tools/collect_evidence.py，断言其产出的 markdown 片段满足质量门：
  1. 含「三件套」（确切命令 / 关键输出 / 截图）各小节；
  2. 命令可被技术读者 copy/paste 复现（出现在 ```bash 围栏内）；
  3. 三件套齐全性校验正确（齐全/缺失判定、--strict 强制失败）；
  4. 输入含 GLOSSARY.md `_Avoid_` 废弃术语时给出预警。

仅依赖标准库（unittest），与 test_validators.py 同一 subprocess 约定。
运行：python -m unittest discover -s tests -t .
"""
import os
import subprocess
import sys
import tempfile
import unittest

from tests._paths import ROOT  # noqa: E402
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

    def test_shot_status_pending_when_hook_only(self):
        # F3 回归：仅给 --shot-cmd（无截图文件）时，清单 shot_status=待补录，
        # 校验表如实标注「待补录」而非「已提供」，但三件套件仍满足（既有契约）。
        import json
        with tempfile.TemporaryDirectory() as tmp:
            out = os.path.join(tmp, "out.md")
            man = os.path.join(tmp, "manifest.jsonl")
            r = run("--step", "s1", "--cmd", "echo hi", "--output", "hi",
                    "--shot-cmd", "screenshot-hook --out /tmp/x.png",
                    "--manifest", man, "--out", out)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            with open(out, encoding="utf-8") as f:
                text = f.read()
            self.assertIn("待补录（钩子命令已记录）", text)
            self.assertNotIn("| 截图 | 是 | 已提供 |", text)
            rec = json.loads(open(man, encoding="utf-8").read().splitlines()[0])
            self.assertEqual(rec["shot_status"], "待补录")
            self.assertTrue(rec["complete"])

    def test_shot_status_provided_with_file(self):
        import json
        with tempfile.TemporaryDirectory() as tmp:
            shot = os.path.join(tmp, "s.png")
            with open(shot, "wb") as f:
                f.write(b"\x89PNG\r\n\x1a\n")
            out = os.path.join(tmp, "out.md")
            man = os.path.join(tmp, "manifest.jsonl")
            r = run("--step", "s1", "--cmd", "echo hi", "--output", "hi",
                    "--screenshot", shot, "--manifest", man, "--out", out)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            rec = json.loads(open(man, encoding="utf-8").read().splitlines()[0])
            self.assertEqual(rec["shot_status"], "已提供")

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


    def test_exam_mode_rejects_hook_only_screenshot(self):
        """AC-02：考试模式下钩子命令不满足截图必需件，strict 必失败。"""
        with tempfile.TemporaryDirectory() as tmp:
            out = os.path.join(tmp, "out.md")
            r = run("--step", "s1", "--cmd", "echo hi", "--output", "hi",
                    "--shot-cmd", "import -window root /tmp/x.png",
                    "--exam", "--strict", "--out", out)
            self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
            self.assertIn("截图（真实文件）", r.stdout + r.stderr)
            with open(out, encoding="utf-8") as f:
                text = f.read()
            self.assertIn("**三件套齐全**：否", text)

    def test_exam_mode_accepts_real_png(self):
        """AC-03：考试模式下真实 PNG（含 IEND）计入完整。"""
        with tempfile.TemporaryDirectory() as tmp:
            shot = os.path.join(tmp, "s.png")
            with open(shot, "wb") as f:
                f.write(b"\x89PNG\r\n\x1a\n" + b"0" * 32 + b"IEND")
            out = os.path.join(tmp, "out.md")
            r = run("--step", "s1", "--cmd", "echo hi", "--output", "hi",
                    "--screenshot", shot, "--exam", "--strict", "--out", out)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            with open(out, encoding="utf-8") as f:
                text = f.read()
            self.assertIn("**三件套齐全**：是。", text)

    def test_exam_mode_fake_path_is_pending_not_provided(self):
        """H1 回归：考试模式无效截图路径不得标「已提供」。"""
        with tempfile.TemporaryDirectory() as tmp:
            out = os.path.join(tmp, "out.md")
            r = run("--step", "s1", "--cmd", "echo hi", "--output", "hi",
                    "--screenshot", os.path.join(tmp, "missing.png"),
                    "--exam", "--strict", "--out", out)
            self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
            with open(out, encoding="utf-8") as f:
                text = f.read()
            self.assertIn("| 截图 | 是 | 待补录（钩子命令已记录） |", text)
            self.assertIn("**三件套齐全**：否", text)

    def test_scored_target_requires_flag_dual(self):
        """AC-05：计分目标模式缺双通道时不完整；--flag 单值仍兼容。"""
        with tempfile.TemporaryDirectory() as tmp:
            shot = os.path.join(tmp, "s.png")
            with open(shot, "wb") as f:
                f.write(b"\x89PNG\r\n\x1a\n" + b"0" * 32 + b"IEND")
            out = os.path.join(tmp, "out.md")
            r = run("--step", "s1", "--cmd", "whoami", "--output", "root",
                    "--screenshot", shot, "--scored-target", "--strict", "--out", out)
            self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
            self.assertIn("flag 双通道", r.stdout + r.stderr)
            r2 = run("--step", "s1", "--cmd", "whoami", "--output", "root",
                     "--screenshot", shot, "--scored-target", "--flag", "FLAG{ok}",
                     "--strict", "--out", out)
            self.assertEqual(r2.returncode, 0, r2.stdout + r2.stderr)


if __name__ == "__main__":
    unittest.main()
