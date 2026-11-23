#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""证据契约测试（AC-10/11/12/13）：三件套、AI 日志四字段、flag 双通道、CLI 复现。"""
import sys
import unittest

from tests._paths import ROOT

if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from tools.attack_multimodal.backends import FakePyRITBackend
from tools.attack_multimodal.runner import run_steps
from tools.attack_multimodal.steps import STEP_IDS, STEP_SPECS


class TestEvidenceContract(unittest.TestCase):
    def test_three_pieces_per_step(self):
        results = run_steps(backend=FakePyRITBackend())
        self.assertEqual(len(results), len(STEP_IDS))
        for r in results:
            self.assertIn("command", r.evidence)
            self.assertIn("screenshot_hook", r.evidence)
            self.assertTrue(r.response.text, r.step_id)

    def test_ai_log_four_fields(self):
        for r in run_steps(backend=FakePyRITBackend()):
            log = r.evidence.get("ai_log")
            self.assertIsInstance(log, dict, r.step_id)
            for f in ("prompt", "model", "output", "adopted"):
                self.assertIn(f, log, r.step_id)
            self.assertTrue(log["prompt"] and log["model"] and log["output"], r.step_id)
            self.assertIsInstance(log["adopted"], bool, r.step_id)

    def test_copy_paste_replay(self):
        from tools.attack_multimodal import demo
        for s in STEP_SPECS:
            self.assertIn("--step %s" % s.step_id, s.command)
            self.assertIn("--target", s.command)
            self.assertEqual(demo.main(["--step", s.step_id, "--target", "http://lab"]), 0)

    def test_flag_dual_channel(self):
        results = run_steps(step_ids=["multimodal-09", "multimodal-10"],
                            backend=FakePyRITBackend())
        flag = results[0].response.text
        self.assertEqual(flag, "OSAI{MM_FAKE_FLAG}")
        shot = results[1].response.text
        self.assertIn("whoami", shot)
        self.assertIn(flag, shot)


class TestDemoCLI(unittest.TestCase):
    def test_list(self):
        from tools.attack_multimodal import demo
        self.assertEqual(demo.main(["--list"]), 0)

    def test_paths(self):
        from tools.attack_multimodal import demo
        self.assertEqual(demo.main(["--paths", "A", "--scenario", "partial"]), 0)

    def test_real_cli_no_crash(self):
        """--real 不因 scenario 关键字崩溃（桩环境下真实后端可构造）。"""
        import unittest.mock as mock
        from tools.attack_multimodal import demo
        # 仅验证 CLI 参数解析与后端构造路径，不连真实端点；用假后端替换真实工厂返回值。
        with mock.patch.object(demo, "get_backend", return_value=FakePyRITBackend()) as gb:
            self.assertEqual(demo.main(["--step", "multimodal-05", "--real"]), 0)
            self.assertTrue(gb.called)

    def test_invalid(self):
        from tools.attack_multimodal import demo
        self.assertEqual(demo.main(["--step", "nope"]), 2)

    def test_undetermined(self):
        from tools.attack_multimodal import demo
        self.assertEqual(demo.main(["--step", "multimodal-08", "--scenario", "undetermined"]), 0)


if __name__ == "__main__":
    unittest.main()
