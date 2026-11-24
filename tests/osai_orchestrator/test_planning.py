"""计划与人在环。"""
from __future__ import annotations

import unittest

from tools.osai_orchestrator.models import Verdict
from tools.osai_orchestrator.planning import (
    ControlAction, HumanInLoop, PlanStep, Planner, RefineOps, Refiner,
)


def step(sid: str) -> PlanStep:
    return PlanStep(sid, "action %s" % sid, "verify %s" % sid)


class PlannerTest(unittest.TestCase):
    def test_valid_plan(self):
        verdict, problems = Planner().build("goal", [step("1"), step("2"), step("3")])
        self.assertIs(verdict, Verdict.PASS)
        self.assertEqual(problems, [])

    def test_step_count_bounds(self):
        verdict, problems = Planner().build("goal", [step("1")])
        self.assertIs(verdict, Verdict.BLOCKED)
        self.assertTrue(any("step count" in p for p in problems))

    def test_duplicate_ids(self):
        verdict, problems = Planner().build("goal", [step("1"), step("1"), step("2")])
        self.assertIs(verdict, Verdict.BLOCKED)
        self.assertIn("duplicate step_id", problems)

    def test_missing_verification(self):
        s = PlanStep("1", "act", "")
        verdict, problems = Planner().build("goal", [s, step("2"), step("3")])
        self.assertIs(verdict, Verdict.BLOCKED)
        self.assertTrue(any("verification" in p for p in problems))

    def test_empty_request(self):
        verdict, problems = Planner().build("  ", [step("1"), step("2"), step("3")])
        self.assertIs(verdict, Verdict.BLOCKED)

    def test_wrap_contains_assignment(self):
        text = Planner().wrap("goal", [step("1"), step("2"), step("3")])
        self.assertIn("<task_assignment>", text)
        self.assertIn("<request>goal</request>", text)


class RefinerTest(unittest.TestCase):
    def test_add_step(self):
        verdict, result, problems = Refiner().apply([step("c")], [step("r1")], RefineOps(add=[step("r2")]))
        self.assertIs(verdict, Verdict.PASS)
        self.assertEqual(len(result), 2)

    def test_completed_step_immutable(self):
        verdict, _, problems = Refiner().apply([step("c")], [step("r1")], RefineOps(remove=["c"]))
        self.assertIs(verdict, Verdict.BLOCKED)
        self.assertTrue(any("completed" in p for p in problems))

    def test_modify_completed_blocked(self):
        verdict, _, _ = Refiner().apply([step("c")], [], RefineOps(modify={"c": step("c")}))
        self.assertIs(verdict, Verdict.BLOCKED)

    def test_reorder(self):
        verdict, result, _ = Refiner().apply([], [step("a"), step("b")], RefineOps(reorder=["b", "a"]))
        self.assertIs(verdict, Verdict.PASS)
        self.assertEqual([s.step_id for s in result], ["b", "a"])

    def test_step_cap(self):
        verdict, _, problems = Refiner().apply([], [step("1")], RefineOps(add=[step("2")]), max_steps=1)
        self.assertIs(verdict, Verdict.BLOCKED)
        self.assertTrue(any("exceeds" in p for p in problems))

    def test_unknown_reorder(self):
        verdict, _, problems = Refiner().apply([], [step("a")], RefineOps(reorder=["z"]))
        self.assertIs(verdict, Verdict.BLOCKED)


class HumanInLoopTest(unittest.TestCase):
    def test_status_is_read_only(self):
        h = HumanInLoop()
        r = h.apply(ControlAction.STATUS, "scope")
        self.assertEqual(r.state, "idle")
        self.assertEqual(h.notes, [])

    def test_stop_changes_state(self):
        h = HumanInLoop()
        r = h.apply(ControlAction.STOP, "scope")
        self.assertEqual(r.state, "stopped")
        self.assertTrue(any("unwritten evidence" in n for n in h.notes))

    def test_submit_requires_scope(self):
        r = HumanInLoop().apply(ControlAction.SUBMIT_INPUT, "  ", "x")
        self.assertFalse(r.accepted)

    def test_patch_effective_next_point(self):
        r = HumanInLoop().apply(ControlAction.PATCH_STEPS, "scope", "ops")
        self.assertIn("next execution point", r.effect)

    def test_wait(self):
        r = HumanInLoop().apply(ControlAction.WAIT, "scope")
        self.assertEqual(r.state, "waiting")


if __name__ == "__main__":
    unittest.main()
