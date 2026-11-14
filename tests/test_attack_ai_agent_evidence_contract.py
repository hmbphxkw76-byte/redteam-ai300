#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""attack-ai-agent 证据契约夹具（S2 / 阶段 9）。

机器强制：稳定步骤标识 aia-01..12 每个恰出现一次
`collect_evidence.py --step aia-NN --strict` 语义，且 12 份证据片段满足
三件套 + AI 交互日志；flag 步骤满足双通道一致与访问证明。

仅依赖标准库（unittest），与既有 `test_*_evidence_contract.py` 同一约定。
运行：python -m unittest discover -s tests
"""
import os
import re
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
IMPL = os.path.join(ROOT, "tools", "attack_ai_agent")
EVIDENCE = os.path.join(ROOT, "evidence", "attack-ai-agent")
STEP_IDS = tuple("aia-%02d" % i for i in range(1, 13))
AVOID_TERMS = ("蜜罐", "rabbit hole", "AI 攻击向量")


class EvidenceContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with open(os.path.join(IMPL, "steps.py"), encoding="utf-8") as f:
            cls.steps_text = f.read()
        with open(os.path.join(IMPL, "runner.py"), encoding="utf-8") as f:
            cls.runner_text = f.read()

    def test_all_twelve_step_ids_declared_exactly_once(self):
        from tools.attack_ai_agent.steps import STEP_IDS as DECLARED
        self.assertEqual(tuple(DECLARED), STEP_IDS)
        for sid in STEP_IDS:
            with self.subTest(step=sid):
                self.assertEqual(
                    len(re.findall(r'StepSpec\("%s"' % sid, self.steps_text)), 1,
                    "步骤 %s 应恰好声明一次" % sid)

    def test_strict_mode_is_mandatory_for_every_evidence_call(self):
        self.assertIn('"--strict"', self.runner_text,
                      "证据发送必须强制 --strict 三件套质量门")
        self.assertIn('"--step"', self.runner_text)
        self.assertIn("EVIDENCE_TOOL", self.runner_text)

    def test_command_is_copy_paste_safe(self):
        from tools.attack_ai_agent.steps import STEP_SPECS
        for spec in STEP_SPECS:
            with self.subTest(step=spec.step_id):
                self.assertNotIn("--target <", spec.command,
                                 "目标占位符未加引号会被 bash 解析为重定向（§6.1）")
                self.assertIn("--step %s" % spec.step_id, spec.command)

    def test_twelve_fragments_complete(self):
        if not os.path.isdir(EVIDENCE):
            self.skipTest("证据片段尚未生成")
        for sid in STEP_IDS:
            path = os.path.join(EVIDENCE, "%s.md" % sid)
            with self.subTest(step=sid):
                self.assertTrue(os.path.isfile(path), "缺少证据片段 %s" % path)
                with open(path, encoding="utf-8") as f:
                    text = f.read()
                self.assertIn("**三件套齐全**：是。", text)
                self.assertIn("#### 确切命令", text)
                self.assertIn("#### 关键输出", text)
                self.assertIn("#### 截图（访问证明）", text)
                self.assertIn("#### AI 交互日志", text)

    def test_flag_steps_have_dual_channel_and_access_proof(self):
        for sid in ("aia-11", "aia-12"):
            path = os.path.join(EVIDENCE, "%s.md" % sid)
            if not os.path.isfile(path):
                self.skipTest("证据片段尚未生成")
            with open(path, encoding="utf-8") as f:
                text = f.read()
            with self.subTest(step=sid):
                self.assertIn("flag 取证（双通道一致）", text)
                self.assertIn("whoami", text)
                self.assertIn("ai_vector.txt", text)

    def test_no_deprecated_terms_in_implementation(self):
        for name in ("steps.py", "runner.py", "backends.py", "paths.py"):
            with open(os.path.join(IMPL, name), encoding="utf-8") as f:
                text = f.read()
            for bad in AVOID_TERMS:
                with self.subTest(file=name, term=bad):
                    self.assertNotIn(bad, text)

    def test_no_legacy_api_names_in_implementation(self):
        for name in os.listdir(IMPL):
            if not name.endswith(".py"):
                continue
            with open(os.path.join(IMPL, name), encoding="utf-8") as f:
                text = f.read()
            for bad in ("pyrit.orchestrator", "Orchestrator(", "AzureOpenAIChatTarget",
                        "XpiaAttack", "ConsoleAttackResultPrinter",
                        "execute_single_turn_attacks_async"):
                with self.subTest(file=name, term=bad):
                    self.assertNotIn(bad, text, "实现中出现已排除 API 名 %s" % bad)


if __name__ == "__main__":
    unittest.main()
