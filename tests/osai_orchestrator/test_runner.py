"""S-1 入口、CLI 与可注入 runner。"""
from __future__ import annotations

import unittest

from tools.osai_orchestrator.cli import main
from tools.osai_orchestrator.governance import ReviewItem
from tools.osai_orchestrator.models import Verdict
from tools.osai_orchestrator.runner import (
    CommandRunner, Orchestrator, RunOutcome, SubprocessRunner,
)


class FakeRunner:
    def __init__(self, outcomes: list[RunOutcome]) -> None:
        self.outcomes = outcomes
        self.calls: list[list[str]] = []

    def run(self, argv):
        self.calls.append(list(argv))
        return self.outcomes.pop(0)


class CommandRunnerTest(unittest.TestCase):
    def test_protocol_shape(self):
        self.assertTrue(hasattr(SubprocessRunner, "run"))
        self.assertTrue(callable(SubprocessRunner.run))

    def test_fake_runner(self):
        r = FakeRunner([RunOutcome(0, "ok", "")])
        outcome = r.run(["echo", "x"])
        self.assertEqual(outcome.returncode, 0)
        self.assertEqual(r.calls[0], ["echo", "x"])

    def test_missing_binary(self):
        outcome = SubprocessRunner().run(["definitely-not-a-real-binary-xyz"])
        self.assertEqual(outcome.returncode, 127)


class OrchestratorTest(unittest.TestCase):
    def test_supervise_pass(self):
        g = Orchestrator().supervise_step("terminal", True)
        self.assertIs(g.verdict, Verdict.PASS)

    def test_reflect_pass_and_block(self):
        o = Orchestrator()
        self.assertIs(o.reflect_step(1, False, False).verdict, Verdict.PASS)
        self.assertIs(o.reflect_step(3, False, False).verdict, Verdict.BLOCKED)

    def test_budget_block(self):
        g = Orchestrator().budget_step("searcher", 18, 5)
        self.assertIs(g.verdict, Verdict.BLOCKED)

    def test_barrier_ready(self):
        g = Orchestrator().barrier_step(True, ["evidence/a"], True, False)
        self.assertIs(g.verdict, Verdict.PASS)

    def test_anonymize(self):
        out = Orchestrator().anonymize("10.1.2.3 password: secret")
        self.assertIn("{target_ip}", out)

    def test_review(self):
        g = Orchestrator().review([ReviewItem("r1", "report.md", True)])
        self.assertIs(g.verdict, Verdict.PASS)


class CLITest(unittest.TestCase):
    def test_plan_lists_capabilities(self):
        import io
        from contextlib import redirect_stdout
        buf = io.StringIO()
        with redirect_stdout(buf):
            code = main(["--plan"])
        self.assertEqual(code, 0)
        out = buf.getvalue()
        self.assertIn("execution-monitor", out)
        self.assertIn("bounded-retriever", out)
        self.assertEqual(len(out.strip().splitlines()), 19)

    def test_anonymize_action(self):
        import io
        from contextlib import redirect_stdout
        buf = io.StringIO()
        with redirect_stdout(buf):
            code = main(["--anonymize", "10.0.0.1"])
        self.assertEqual(code, 0)
        self.assertIn("{target_ip}", buf.getvalue())

    def test_no_action(self):
        self.assertEqual(main([]), 2)

    def test_bad_config(self):
        self.assertEqual(main(["--config", "/nonexistent/config.json"]), 2)


if __name__ == "__main__":
    unittest.main()
