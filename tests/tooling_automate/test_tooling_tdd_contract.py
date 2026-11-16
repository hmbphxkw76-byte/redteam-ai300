"""阶段 9 TDD 契约补强（v2 AC-08/10/11/13/14/16）。

按 v2「判定方式」列名逐条锁定外部行为；每条先红后绿，见 gate-stage9。
"""
import contextlib
import io
import json
import os
import pathlib
import tempfile
import unittest

from tools.tooling_automate import main as public_main
from tools.tooling_automate import manifest as M
from tools.tooling_automate.runner import PlanResult, RunOutcome, StepResult, run_plan
from tools.tooling_automate.summary import render_markdown
from tests.support.tooling_fakes import FakeRunner, make_task, make_task_dict

PKG = pathlib.Path(__file__).resolve().parent.parent / "tools" / "tooling_automate"


def manifest_file(d, tasks):
    p = os.path.join(d, "m.json")
    with open(p, "w", encoding="utf-8") as f:
        json.dump({"tasks": tasks}, f)
    return p


class TddContractTests(unittest.TestCase):
    def test_public_entrypoint(self):
        """AC-08：公开入口 main 可注入 runner（CLI 与库共用 S-1）。"""
        with tempfile.TemporaryDirectory() as d:
            p = manifest_file(d, [make_task_dict("e-01")])
            fr = FakeRunner()
            with contextlib.redirect_stdout(io.StringIO()):
                code = public_main(["--manifest", p, "--out", "-"], runner=fr)
        self.assertEqual(code, 0)
        self.assertEqual(len(fr.calls), 1)
        self.assertIn("tools/collect_evidence.py", fr.calls[0])

    def test_exit_codes_three_state(self):
        """AC-13：全通过 0 / 门禁失败 1 / 用法错误 2。"""
        ok = run_plan(M.Manifest(tasks=[make_task("e-01")]), runner=FakeRunner())
        self.assertEqual(ok.exit_code, 0)
        bad = run_plan(M.Manifest(tasks=[make_task("e-01")]),
                       runner=FakeRunner(outcomes={"tools/collect_evidence.py": RunOutcome(1)}))
        self.assertEqual(bad.exit_code, 1)
        with tempfile.TemporaryDirectory() as d:
            p = manifest_file(d, [make_task_dict("e-01"), make_task_dict("e-01")])
            with contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(public_main(["--manifest", p]), 2)

    def test_usage_error_no_passed_field(self):
        """AC-14：用法错误 stdout 无 passed 字段。"""
        with tempfile.TemporaryDirectory() as d:
            p = manifest_file(d, [make_task_dict("bad")])
            out = io.StringIO()
            with contextlib.redirect_stdout(out), contextlib.redirect_stderr(io.StringIO()):
                code = public_main(["--manifest", p])
        self.assertEqual(code, 2)
        self.assertNotIn("passed", out.getvalue())

    def test_reuse_declaration_every_row(self):
        """AC-10：每件输出含复用声明。"""
        man = M.Manifest(tasks=[make_task("e-01"), make_task("e-02")])
        res = PlanResult(results=[StepResult(man.tasks[0], ["python", "tools/collect_evidence.py"],
                                             RunOutcome(0), True),
                                  StepResult(man.tasks[1], ["python", "tools/collect_evidence.py"],
                                             RunOutcome(0), True)], coverage=1.0, manual=[], exit_code=0)
        text = render_markdown(res, "-", man)
        rows = [ln for ln in text.splitlines() if ln.startswith("| e-")]
        self.assertEqual(len(rows), 2)
        for row in rows:
            self.assertIn("复用", row)
            self.assertIn("零新增 seam", row)

    def test_summary_consumable(self):
        """AC-11：汇总含覆盖率与剩余手动清单，结构可直读。"""
        man = M.Manifest(tasks=[make_task("e-01"), make_task("e-02", manual=True)])
        res = PlanResult(results=[StepResult(man.tasks[0], [], RunOutcome(0), True)],
                         coverage=0.5, manual=[man.tasks[1]], exit_code=0)
        text = render_markdown(res, "-", man)
        self.assertIn("自动化覆盖率：0.50", text)
        self.assertIn("剩余手动任务：1", text)
        self.assertIn("（手动）", text)

    def test_no_gate_redefinition(self):
        """AC-16：编排层无等价校验器实现。"""
        for f in PKG.rglob("*.py"):
            text = f.read_text(encoding="utf-8")
            for banned in ("def validate_skill", "def check_glossary", "def check_token_budget"):
                self.assertNotIn(banned, text)


if __name__ == "__main__":
    unittest.main()
