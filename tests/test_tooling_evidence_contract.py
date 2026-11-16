"""证据契约测试（AC-05 严格模式 / AC-12 命名）。"""
import unittest

from tools.tooling_automate import manifest as M
from tools.tooling_automate.reuse import build_collect_evidence_argv
from tools.tooling_automate.runner import PlanResult, RunOutcome, run_plan
from tests.tooling_fakes import FakeRunner, make_task


class EvidenceContractTests(unittest.TestCase):
    def test_strict_evidence_argv(self):
        argv = build_collect_evidence_argv(make_task("rag-07", cmd="echo probe"))
        i = argv.index("--step")
        self.assertEqual(argv[i + 1], "rag-07")  # <prefix>-NN 命名透传
        self.assertIn("--strict", argv)
        self.assertIn("--out", argv)

    def test_naming_convention_passthrough(self):
        for step in ("recon-01", "attack-12", "verify-evidence-03"):
            argv = build_collect_evidence_argv(make_task(step, cmd="x"))
            self.assertEqual(argv[argv.index("--step") + 1], step)

    def test_strict_failure_propagates(self):
        fr = FakeRunner(outcomes={"tools/collect_evidence.py": RunOutcome(1, "", "triplet mismatch")})
        man = M.Manifest(tasks=[M.Task(
            category="enum", target="h1", step="e-01", inputs={"cmd": "x"},
            outputs={"evidence": "ev.md"}, trigger="t", classification="auto", raw={})])
        res = run_plan(man, runner=fr)
        self.assertEqual(res.exit_code, 1)
        self.assertIsInstance(res, PlanResult)


if __name__ == "__main__":
    unittest.main()
