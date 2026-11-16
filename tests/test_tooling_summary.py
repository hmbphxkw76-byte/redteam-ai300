"""summary 切片测试（AC-03/09/10/11）。"""
import os
import tempfile
import unittest

from tools.tooling_automate import manifest as M
from tools.tooling_automate.runner import PlanResult, RunOutcome, StepResult
from tools.tooling_automate.summary import compute_coverage, render_markdown
from tests.tooling_fakes import make_task


def man_with(steps):
    return M.Manifest(tasks=list(steps))


class SummaryTests(unittest.TestCase):
    def test_coverage_denominator(self):
        man = man_with([make_task("e-01"), make_task("e-02"),
                        make_task("e-03", manual=True)])
        # 2 可脚本化：1 通过 1 失败 → 0.5
        results = [
            StepResult(man.tasks[0], [], RunOutcome(0), True),
            StepResult(man.tasks[1], [], RunOutcome(1), False),
            # manual 不进入 results
        ]
        self.assertAlmostEqual(compute_coverage(man, results), 0.5)

    def test_coverage_empty(self):
        man = man_with([make_task("e-01", manual=True)])
        self.assertEqual(compute_coverage(man, []), 0.0)

    def test_markdown_summary(self):
        man = man_with([make_task("e-01"), make_task("e-02", manual=True)])
        res = PlanResult(results=[StepResult(man.tasks[0], ["python", "tools/collect_evidence.py"],
                                            RunOutcome(0), True)],
                         coverage=1.0, manual=[man.tasks[1]], exit_code=0)
        text = render_markdown(res, "-", man)
        self.assertIn("自动化覆盖率：1.00", text)
        self.assertIn("复用", text)
        self.assertIn("e-01", text)
        self.assertIn("（手动）", text)

    def test_render_writes_file(self):
        man = man_with([make_task("e-01")])
        res = PlanResult(results=[StepResult(man.tasks[0], [], RunOutcome(0), True)],
                         coverage=1.0, manual=[], exit_code=0)
        with tempfile.TemporaryDirectory() as d:
            out = os.path.join(d, "sum.md")
            render_markdown(res, out, man)
            self.assertTrue(os.path.exists(out))


if __name__ == "__main__":
    unittest.main()
