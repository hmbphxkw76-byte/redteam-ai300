#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""attack-infra 证据契约夹具（S2）。

将 attack-infra SKILL.md 的「每步命令 + 输出 + 截图」质量门语义从人工复核
升级为机器强制：断言声明于 SKILL.md 的 infra-01…infra-08 每个 step_id 均出现一次
`collect_evidence.py --step infra-0N` 调用模式（镜像既有夹具）。

仅依赖标准库（unittest）。运行：python -m unittest discover -s tests
"""
import os
import re
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKILL = os.path.join(ROOT, "skills", "attack-infra", "SKILL.md")
STEP_IDS = ["infra-0%d" % i for i in range(1, 9)]
AVOID_TERMS = ("蜜罐", "rabbit hole", "AI 攻击向量")


class AttackInfraEvidenceContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not os.path.isfile(SKILL):
            raise unittest.SkipTest("skills/attack-infra/SKILL.md 不存在")
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

class AttackInfraRunnerContractTests(unittest.TestCase):
    """T5 强化：八步运行时证据记录必须满足三件套字段与五值结论（AC-15）。"""

    def _run(self):
        import importlib
        runner = importlib.import_module("tools.attack_infra.runner")
        model = importlib.import_module("tools.attack_infra.model")
        transport = importlib.import_module("tools.attack_infra.transport")
        evidence = importlib.import_module("tools.attack_infra.evidence")
        command = importlib.import_module("tools.attack_infra.command")
        fake = evidence.FakeEvidence()
        ctx = model.RunContext(
            target="h", transport=transport.FakeTransport({}, default=transport.HttpResponse(
                status=200, content_type="text/html", body="<html></html>")),
            command=command.FakeCommand({}, default=command.CommandResult(
                code=127, stderr="not found")),
            evidence=fake, timeout=5, ports=(11434,))
        report = runner.run(ctx)
        return fake.records, report

    def test_each_step_record_has_command_output_and_shot(self):
        records, _ = self._run()
        self.assertEqual(len(records), 8)
        for record in records:
            with self.subTest(step=record["step_id"]):
                self.assertTrue(record["command"].strip(),
                                "缺少确切命令")
                self.assertTrue(record["output"].strip(),
                                "缺少关键输出")
                self.assertTrue(record.get("shot_cmd") or record.get("screenshot"),
                                "缺少截图钩子")

    def test_outcomes_are_within_five_values(self):
        _, report = self._run()
        allowed = {"ABSENT", "AUTH_REQUIRED", "EXPOSED_NO_AUTH",
                   "EXPLOITED", "BLOCKED"}
        self.assertEqual({s.outcome.value for s in report.steps} - allowed, set())


if __name__ == "__main__":
    unittest.main()
