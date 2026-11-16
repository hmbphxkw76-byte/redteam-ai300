#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""attack-rag 证据契约夹具（S2）。

把 SKILL.md「每步命令 + 输出 + 截图」质量门从人工复核升级为机器强制：
经真实 `tools/collect_evidence.py` 落盘，断言
  ① 每个 step_id 恰好一次 `--step rag-NN` 收口；
  ② 三件套齐全 + 五件套校验表存在；
  ③ 含 LLM 的步骤带 AI 交互日志（prompt/模型/输出/采纳）；
  ④ flag 双通道一致才通过严格模式，不一致必须退出码 1；
  ⑤ 术语符合 GLOSSARY（无废弃词）。

运行：python -m unittest tests.test_attack_rag_evidence_contract
"""
import os
import tempfile
import unittest

from tools.attack_rag import AttackRequest, FakeBackend, Runtime, run_attack
from tools.attack_rag.evidence import EvidenceWriter, RecordingWriter
from tools.attack_rag.steps import STEP_IDS, STEP_SPECS

from tests._paths import ROOT  # noqa: E402
DEMO = os.path.join(ROOT, "skills", "attack-rag", "examples", "evidence-demo.md")
SMALL = 60
AVOID_TERMS = ("蜜罐", "rabbit hole")
REQUIRED_SECTIONS = ("#### 确切命令", "#### 关键输出", "#### 截图（访问证明）",
                     "#### 证据校验（五件套 / 三件套）", "**三件套齐全**：是。")
AI_STEPS = ("rag-02", "rag-03", "rag-04")


class AttackRagEvidenceContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.dir = cls.tmp.name
        cls.request = AttackRequest(target="rag-harness", corpus_size=SMALL,
                                    evidence_dir=cls.dir)
        cls.report = run_attack(
            cls.request,
            Runtime(backend=FakeBackend(),
                    writer=EvidenceWriter(cls.dir, tool_path=cls.tool_path())))

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    @staticmethod
    def tool_path():
        return os.path.join(ROOT, "tools", "collect_evidence.py")

    def _read(self, step_id):
        path = os.path.join(self.dir, "%s.md" % step_id)
        self.assertTrue(os.path.isfile(path), "缺少证据片段 %s" % path)
        with open(path, encoding="utf-8") as handle:
            return handle.read()

    def test_every_step_emitted_once(self):
        writer = RecordingWriter()
        run_attack(self.request, Runtime(backend=FakeBackend(), writer=writer))
        self.assertEqual([c["step_id"] for c in writer.calls], list(STEP_IDS))
        self.assertEqual(len(writer.calls), len(STEP_IDS))

    def test_fragment_has_three_pieces_and_table(self):
        for step_id in STEP_IDS:
            with self.subTest(step=step_id):
                text = self._read(step_id)
                for section in REQUIRED_SECTIONS:
                    self.assertIn(section, text)
                self.assertIn("collect_evidence.py", text)
                self.assertIn("--step %s" % step_id, text)

    def test_llm_steps_have_ai_interaction_log(self):
        for step_id in AI_STEPS:
            with self.subTest(step=step_id):
                text = self._read(step_id)
                self.assertIn("#### AI 交互日志", text)
                for field in ("prompt:", "模型:", "输出:", "采纳:"):
                    self.assertIn(field, text)

    def test_non_llm_step_has_no_ai_log_section(self):
        self.assertNotIn("#### AI 交互日志", self._read("rag-01"))

    def test_flag_dual_channel_consistent_in_fragment(self):
        with tempfile.TemporaryDirectory() as tmp:
            request = AttackRequest(step="rag-05", corpus_size=SMALL,
                                    evidence_dir=tmp,
                                    flag_panel="FLAG{demo}",
                                    flag_shot="FLAG{demo}")
            run_attack(request, Runtime(backend=FakeBackend(),
                                        writer=EvidenceWriter(tmp, tool_path=self.tool_path())))
            with open(os.path.join(tmp, "rag-05.md"), encoding="utf-8") as handle:
                text = handle.read()
        self.assertIn("#### flag 取证（双通道一致）", text)
        self.assertIn("| 一致性 | **一致** |", text)
        self.assertIn("FLAG{demo}", text)

    def test_flag_mismatch_fails_strict_mode(self):
        writer = EvidenceWriter(self.dir, tool_path=self.tool_path())
        _path, code, err = writer.emit(
            step_id="rag-05-check", command="python tools/attack_rag/cli.py --step rag-05",
            output="ai_vector.txt: FLAG{a}", target="rag-harness",
            title="flag 双通道严格模式", shot_cmd="screenshot-hook --out /tmp/x.png",
            flag_panel="FLAG{a}", flag_shot="FLAG{b}", strict=True)
        self.assertEqual(code, 1, "flag 双通道不一致时严格模式必须失败")
        self.assertIn("flag", err.lower())

    def test_missing_output_fails_strict_mode(self):
        writer = EvidenceWriter(self.dir, tool_path=self.tool_path())
        _path, code, err = writer.emit(
            step_id="rag-01-check", command="echo hi", output="",
            target="rag-harness", shot_cmd="screenshot-hook --out /tmp/x.png",
            strict=True)
        self.assertEqual(code, 1, "三件套不全时严格模式必须失败")
        self.assertIn("三件套", err)

    def test_fragments_avoid_deprecated_terms(self):
        for step_id in STEP_IDS:
            text = self._read(step_id)
            for bad in AVOID_TERMS:
                self.assertNotIn(bad, text)

    def test_demo_step_ids_align_with_contract(self):
        if not os.path.isfile(DEMO):
            self.skipTest("evidence-demo.md 不存在")
        with open(DEMO, encoding="utf-8") as handle:
            demo = handle.read()
        titles = {s.step_id: s.title for s in STEP_SPECS}
        for step_id in ("rag-01", "rag-02"):
            self.assertIn("步骤 %s：%s" % (step_id, titles[step_id]), demo,
                          "示例证据与步骤契约标题不一致，会导致 report-exam 复用错位")

    def test_report_matches_fragments(self):
        for verdict in self.report.verdicts:
            self.assertTrue(os.path.isfile(verdict.evidence_path))
            self.assertIn(verdict.level, ("完全生效", "部分生效", "未生效", "已跳过"))


if __name__ == "__main__":
    unittest.main()
