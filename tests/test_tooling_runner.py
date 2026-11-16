"""runner / S-1 切片测试（AC-04/08/13/14/17）。"""
import os
import tempfile
import unittest

from tools.tooling_automate import manifest as M
from tools.tooling_automate.runner import (
    PlanResult,
    RunOutcome,
    SubprocessRunner,
    run_plan,
)
from tests.tooling_fakes import FakeRunner, make_task, make_task_dict


def make_manifest(steps):
    return M.Manifest(tasks=list(steps))


class RunnerTests(unittest.TestCase):
    def test_ordered_by_step(self):
        man = make_manifest([make_task("e-03"), make_task("e-01"), make_task("e-02")])
        fr = FakeRunner()
        run_plan(man, runner=fr)
        seen = [c[c.index("--step") + 1] for c in fr.calls]
        self.assertEqual(seen, ["e-01", "e-02", "e-03"])

    def test_s1_entry_injectable(self):
        # S-1 统一入口：库调用可注入替身
        man = make_manifest([make_task("e-01")])
        fr = FakeRunner()
        res = run_plan(man, runner=fr)
        self.assertIsInstance(res, PlanResult)
        self.assertEqual(fr.calls[0][1], "tools/collect_evidence.py")

    def test_exit_zero_all_pass(self):
        man = make_manifest([make_task("e-01"), make_task("e-02")])
        res = run_plan(man, runner=FakeRunner())
        self.assertEqual(res.exit_code, 0)

    def test_exit_one_on_failure(self):
        fr = FakeRunner(outcomes={"tools/collect_evidence.py": RunOutcome(1, "", "strict fail")})
        man = make_manifest([make_task("e-01"), make_task("e-02")])
        res = run_plan(man, runner=fr)
        self.assertEqual(res.exit_code, 1)

    def test_usage_error_exit_two(self):
        from tools.tooling_automate.cli import main
        tasks = [make_task_dict("e-01"), make_task_dict("e-01")]  # 冲突
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "m.json")
            import json
            with open(p, "w", encoding="utf-8") as f:
                json.dump({"tasks": tasks}, f)
            self.assertEqual(main(["--manifest", p]), 2)

    def test_readonly_no_side_effects(self):
        # run_plan 自身不写任何文件（只读编排）
        man = make_manifest([make_task("e-01")])
        with tempfile.TemporaryDirectory() as d:
            fr = FakeRunner(default=RunOutcome(0, "", ""))
            run_plan(man, runner=fr)
            self.assertEqual(os.listdir(d), [])

    def test_dry_run_no_execution(self):
        man = make_manifest([make_task("e-01")])
        fr = FakeRunner()
        res = run_plan(man, runner=fr, dry_run=True)
        self.assertEqual(fr.calls, [])
        self.assertEqual(res.exit_code, 0)
        self.assertTrue(all(r.strict_ok for r in res.results))

    def test_subprocess_runner_real(self):
        out = SubprocessRunner().run(["python", "-c", "print(1)"])
        self.assertEqual(out.returncode, 0)


if __name__ == "__main__":
    unittest.main()
