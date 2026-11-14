#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""attack-ai-agent 单缝行为测试（S2 / 阶段 9）。

只经唯一公开入口 `run_attack` 断言外部行为，不直达对象图构造等实现细节
（AC-23 / AC-25 / §3.9-⑤）。四组响应：注入生效 / 记忆召回 / 越权外呼 / 拒绝；
另覆盖部分生效、失败与豁免、flag 双通道与零 pyrit 依赖。

运行：python -m unittest discover -s tests
"""
import importlib.util
import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from tools.attack_ai_agent import run_attack
from tools.attack_ai_agent.backends import FakePyRITBackend, TargetResponse
from tools.attack_ai_agent.runner import grade
from tools.attack_ai_agent.steps import STEP_IDS


def collect(spec, response, level, graph, target, evidence_dir):
    """证据发送替身：只记录调用，不落盘（测试替身可替换外部依赖）。"""
    collect.calls.append(spec.step_id)
    return os.path.join(evidence_dir, "%s.md" % spec.step_id)


collect.calls = []


class RunnerBehaviourTests(unittest.TestCase):
    def setUp(self):
        collect.calls = []

    def _run(self, **kw):
        kw.setdefault("emitter", collect)
        return run_attack(objective="取证 ai_vector.txt", **kw)

    def test_effective_scenario_emits_twelve_evidence_calls(self):
        report = self._run(backend_factory=FakePyRITBackend(scenario="effective"))
        self.assertEqual(report.backend, "fake-stdlib")
        self.assertEqual(tuple(v.step_id for v in report.verdicts), STEP_IDS)
        self.assertEqual(tuple(collect.calls), STEP_IDS)
        self.assertTrue(all(v.level == "完全生效" for v in report.verdicts))

    def test_refusal_records_not_effective_without_exaggeration(self):
        report = self._run(backend_factory=FakePyRITBackend(scenario="refusal"))
        self.assertTrue(all(v.level == "未生效" for v in report.verdicts))
        self.assertTrue(all("生效" not in v.output or "未生效" in v.output
                            for v in report.verdicts))

    def test_partial_scenario_is_graded_partial(self):
        report = self._run(backend_factory=FakePyRITBackend(scenario="partial"))
        self.assertTrue(all(v.level == "部分生效" for v in report.verdicts))
        self.assertFalse(any(v.deterministic_hit for v in report.verdicts))

    def test_skips_memory_path_when_no_persistent_memory(self):
        backend = FakePyRITBackend(memory_available=False)
        report = self._run(backend_factory=backend)
        by_id = {v.step_id: v for v in report.verdicts}
        for sid in ("aia-05", "aia-06", "aia-07"):
            self.assertEqual(by_id[sid].level, "已跳过")
            self.assertEqual(by_id[sid].skip_reason, "no_persistent_memory")
        self.assertEqual(by_id["aia-02"].level, "完全生效")

    def test_skips_tool_path_when_no_callable_tools(self):
        backend = FakePyRITBackend(tools_available=False)
        report = self._run(backend_factory=backend)
        by_id = {v.step_id: v for v in report.verdicts}
        for sid in ("aia-08", "aia-09", "aia-10"):
            self.assertEqual(by_id[sid].level, "已跳过")
            self.assertEqual(by_id[sid].skip_reason, "no_callable_tools")

    def test_single_step_request_runs_only_that_step(self):
        report = self._run(step="aia-09", backend_factory=FakePyRITBackend())
        self.assertEqual([v.step_id for v in report.verdicts], ["aia-09"])
        self.assertEqual(collect.calls, ["aia-09"])

    def test_unknown_step_is_rejected(self):
        with self.assertRaises(ValueError):
            self._run(step="aia-99")

    def test_exfiltration_response_is_recorded_as_evidence_output(self):
        report = self._run(step="aia-09", backend_factory=FakePyRITBackend())
        self.assertIn("exfil.example", report.verdicts[0].output)

    def test_grade_is_deterministic_pure_function(self):
        self.assertEqual(grade(TargetResponse("x", "", True, True)), "完全生效")
        self.assertEqual(grade(TargetResponse("x", "", False, True)), "部分生效")
        self.assertEqual(grade(TargetResponse("x", "", False, False)), "未生效")
        self.assertEqual(grade(TargetResponse("x", "已跳过", True, True)), "已跳过")

    def test_object_graphs_cover_three_paths_and_b7_exception(self):
        report = self._run(step="aia-02", backend_factory=FakePyRITBackend())
        self.assertEqual(len(report.graphs), 3)
        self.assertEqual([g["owasp"] for g in report.graphs],
                         ["ASI01", "ASI06", "ASI02"])
        self.assertTrue(report.graphs[0]["notes"])
        self.assertEqual(report.graphs[1]["memory_db_type"], "SQLite")

    def test_pyrit_not_required_at_import_time(self):
        self.assertIsNone(importlib.util.find_spec("pyrit"),
                          "本用例验证零依赖环境；若已安装 pyrit 则应改为子进程隔离验证")
        spec = importlib.util.find_spec("tools.attack_ai_agent")
        self.assertIsNotNone(spec)

    def test_emit_false_skips_evidence_writes(self):
        report = run_attack(objective="x", step="aia-01", emit=False,
                            backend_factory=FakePyRITBackend())
        self.assertEqual(report.evidence_paths(), ("",))

    def test_batch_objectives_are_all_executed(self):
        """AC-13：AttackExecutor 批量跑过多个 objective。"""
        backend = FakePyRITBackend()
        report = self._run(step="aia-02", backend_factory=backend,
                           objectives=["目标甲", "目标乙"])
        self.assertEqual(tuple(report.objectives), ("目标甲", "目标乙"))
        self.assertEqual([o for _, o in backend.calls], ["目标甲", "目标乙"])


if __name__ == "__main__":
    unittest.main()
