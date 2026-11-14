#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""attack-multi-agent 证据契约夹具（S2）。

将 attack-multi-agent SKILL.md 的「每步命令 + 输出 + 截图」质量门语义从人工复核
升级为机器强制：断言声明于 SKILL.md 的 a2a-01…a2a-08 每个 step_id 均出现一次
`collect_evidence.py --step a2a-0N` 调用模式（镜像 recon/foothold/mcp/embeddings 既有夹具）。

仅依赖标准库（unittest）。运行：python -m unittest discover -s tests
"""
import os
import re
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKILL = os.path.join(ROOT, "skills", "attack-multi-agent", "SKILL.md")
STEP_IDS = ["a2a-0%d" % i for i in range(1, 9)]
AVOID_TERMS = ("蜜罐", "rabbit hole", "AI 攻击向量")


class AttackMultiAgentEvidenceContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not os.path.isfile(SKILL):
            raise unittest.SkipTest("skills/attack-multi-agent/SKILL.md 不存在")
        with open(SKILL, encoding="utf-8") as f:
            cls.text = f.read()

    def _assert_step_has_evidence_call(self, step_id):
        self.assertIn(step_id, self.text,
                      "SKILL.md 未声明步骤 %s" % step_id)
        pattern = re.compile(
            r"collect_evidence\.py[^\n]*--step\s+%s\b" % re.escape(step_id)
        )
        self.assertRegex(
            self.text, pattern,
            "步骤 %s 未出现 `collect_evidence.py --step %s` 调用"
            "（质量门证据契约缺失，S2 应机器强制拦截）" % (step_id, step_id),
        )

    def test_all_eight_steps_declared_with_evidence_calls(self):
        for sid in STEP_IDS:
            with self.subTest(step=sid):
                self._assert_step_has_evidence_call(sid)

    def test_exactly_eight_evidence_calls(self):
        matches = 0
        for sid in STEP_IDS:
            pattern = re.compile(
                r"collect_evidence\.py[^\n]*--step\s+%s\b" % re.escape(sid)
            )
            if pattern.search(self.text):
                matches += 1
        self.assertEqual(matches, 8,
                         "应恰好 8 个 step 各有一次 collect_evidence 调用，实得 %d" % matches)

    def test_no_avoid_terms_in_skill(self):
        for bad in AVOID_TERMS:
            self.assertNotIn(bad, self.text,
                             "SKILL.md 使用了废弃术语 %r（应改用 GLOSSARY 规范词）" % bad)


if __name__ == "__main__":
    unittest.main()
