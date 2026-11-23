#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""证据契约测试（AC-10/11/12/13）：三/五件套字段与 flag 双通道。

仅标准库。断言每步证据含命令/截图钩子/AI 日志四字段，flag 步骤双通道一致。
"""
import sys
import unittest

from tests._paths import ROOT

if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from tools.attack_jailbreak.backends import FakePyRITBackend
from tools.attack_jailbreak.runner import run_steps
from tools.attack_jailbreak.steps import STEP_IDS, STEP_SPECS


class TestEvidenceContract(unittest.TestCase):
    def test_three_pieces_per_step(self):
        """AC-10：命令 + 输出 + 截图钩子三字段齐全。"""
        results = run_steps(backend=FakePyRITBackend())
        self.assertEqual(len(results), len(STEP_IDS))
        for r in results:
            self.assertIn("command", r.evidence)
            self.assertIn("screenshot_hook", r.evidence)
            self.assertTrue(r.response.text, r.step_id)

    def test_ai_log_four_fields(self):
        """AC-11：每步 ai_log 含 prompt/模型/输出/采纳修改四字段（C8 §6.3）。"""
        for r in run_steps(backend=FakePyRITBackend()):
            log = r.evidence.get("ai_log")
            self.assertIsInstance(log, dict, r.step_id)
            for field in ("prompt", "model", "output", "adopted"):
                self.assertIn(field, log, r.step_id)
            self.assertTrue(log["prompt"], r.step_id)
            self.assertTrue(log["model"], r.step_id)
            self.assertTrue(log["output"], r.step_id)
            self.assertIsInstance(log["adopted"], bool, r.step_id)

    def test_copy_paste_replay(self):
        """AC-12：每步可按路径 copy/paste 复现；命令行参数被 CLI 接受（S1）。"""
        from tools.attack_jailbreak import demo
        for s in STEP_SPECS:
            self.assertIn("--step %s" % s.step_id, s.command)
            self.assertIn("--target", s.command)
            # 用命令中的参数顺序真实调用 parser，确保不再出现 unrecognized arguments
            args = ["--step", s.step_id, "--target", "http://lab"]
            self.assertEqual(demo.main(args), 0, s.command)

    def test_flag_dual_channel(self):
        """AC-13：flag 面板值与截图/正文逐字一致（不伪造）。"""
        results = run_steps(step_ids=["jailbreak-09", "jailbreak-10"],
                            backend=FakePyRITBackend())
        flag = results[0].response.text
        self.assertEqual(flag, "OSAI{FAKE_FLAG}")
        shot = results[1].response.text
        self.assertIn("whoami", shot)
        # 访问证明 + 双通道逐字一致：截图/正文中包含面板 flag 值
        self.assertIn(flag, shot)


class TestDemoCLI(unittest.TestCase):
    """覆盖 demo CLI 外部行为（提升 demo.py 覆盖率，AC-20）。"""

    def test_list(self):
        from tools.attack_jailbreak import demo
        self.assertEqual(demo.main(["--list"]), 0)

    def test_single_step(self):
        from tools.attack_jailbreak import demo
        self.assertEqual(demo.main(["--step", "jailbreak-02"]), 0)

    def test_paths(self):
        from tools.attack_jailbreak import demo
        self.assertEqual(demo.main(["--paths", "A", "--scenario", "partial"]), 0)

    def test_invalid_step(self):
        from tools.attack_jailbreak import demo
        self.assertEqual(demo.main(["--step", "bogus"]), 2)

    def test_undetermined_scenario(self):
        from tools.attack_jailbreak import demo
        self.assertEqual(demo.main(["--step", "jailbreak-08",
                                    "--scenario", "undetermined"]), 0)


if __name__ == "__main__":
    unittest.main()
