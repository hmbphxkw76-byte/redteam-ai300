"""运行时监督：监控、反思、上限、栅栏。"""
from __future__ import annotations

import unittest

from tools.osai_orchestrator.models import Decision, LimitConfig, Verdict
from tools.osai_orchestrator.supervision import (
    Barrier, BarrierKind, ExecutionMonitor, Reflector, ToolCallBudget,
)


class ExecutionMonitorTest(unittest.TestCase):
    def test_pass_when_advancing(self):
        m = ExecutionMonitor(LimitConfig(same_tool_limit=5, total_tool_limit=10))
        v = m.observe("terminal", True)
        self.assertIs(v.verdict, Verdict.PASS)
        self.assertEqual(v.same_tool_count, 1)

    def test_same_tool_threshold_trips(self):
        m = ExecutionMonitor(LimitConfig(same_tool_limit=3, total_tool_limit=100))
        for _ in range(2):
            v = m.observe("terminal", True)
        self.assertIs(v.verdict, Verdict.PASS)
        v = m.observe("terminal", True)
        self.assertIs(v.verdict, Verdict.BLOCKED)
        self.assertIn("identical", v.advice)

    def test_no_progress_trips_immediately(self):
        m = ExecutionMonitor(LimitConfig(same_tool_limit=99, total_tool_limit=99))
        v = m.observe("terminal", False)
        self.assertIs(v.verdict, Verdict.BLOCKED)
        self.assertIn("no measurable progress", v.advice)

    def test_total_ceiling_trips(self):
        m = ExecutionMonitor(LimitConfig(same_tool_limit=99, total_tool_limit=2))
        m.observe("a", True)
        v = m.observe("b", True)
        self.assertIs(v.verdict, Verdict.BLOCKED)

    def test_reset_clears_history(self):
        m = ExecutionMonitor(LimitConfig(same_tool_limit=2, total_tool_limit=99))
        m.observe("a", True)
        m.reset()
        v = m.observe("a", True)
        self.assertEqual(v.same_tool_count, 1)


class ReflectorTest(unittest.TestCase):
    def test_below_threshold_continues(self):
        self.assertIs(Reflector(3).reflect(2, False, False).decision, Decision.CONTINUE)

    def test_threshold_with_action_continues(self):
        self.assertIs(Reflector(3).reflect(3, True, False).decision, Decision.CONTINUE)

    def test_threshold_without_action_terminates(self):
        r = Reflector(3).reflect(3, False, False)
        self.assertIs(r.decision, Decision.TERMINATE)
        self.assertTrue(r.ready_to_stop)

    def test_near_limit_terminates_first(self):
        r = Reflector(3).reflect(0, True, True)
        self.assertIs(r.decision, Decision.TERMINATE)


class ToolCallBudgetTest(unittest.TestCase):
    def test_role_ceiling(self):
        b = ToolCallBudget()
        self.assertEqual(b.ceiling("searcher"), 20)
        self.assertEqual(b.ceiling("pentester"), 100)

    def test_pass_within_ceiling(self):
        verdict, findings = ToolCallBudget().check("searcher", 5, 10)
        self.assertIs(verdict, Verdict.PASS)
        self.assertEqual(findings, [])

    def test_blocked_over_ceiling(self):
        verdict, findings = ToolCallBudget().check("searcher", 15, 10)
        self.assertIs(verdict, Verdict.BLOCKED)
        self.assertEqual(len(findings), 2)

    def test_negative_used_rejected(self):
        with self.assertRaises(ValueError):
            ToolCallBudget().check("pentester", -1, 0)


class BarrierTest(unittest.TestCase):
    def test_done_when_all_satisfied(self):
        d = Barrier().decide(True, ["evidence/a"], True, False)
        self.assertIs(d.kind, BarrierKind.DONE)
        self.assertFalse(d.needs_confirmation)

    def test_ask_when_scope_unconfirmed(self):
        self.assertIs(Barrier().decide(True, ["e"], True, True).kind, BarrierKind.ASK)

    def test_ask_without_evidence(self):
        self.assertIs(Barrier().decide(True, [], True, False).kind, BarrierKind.ASK)

    def test_ask_without_dual_channel(self):
        self.assertIs(Barrier().decide(True, ["e"], False, False).kind, BarrierKind.ASK)

    def test_ask_when_objective_unmet(self):
        d = Barrier().decide(False, ["e"], True, False)
        self.assertIs(d.kind, BarrierKind.ASK)
        self.assertIn("objective not met", d.reasons)


if __name__ == "__main__":
    unittest.main()
