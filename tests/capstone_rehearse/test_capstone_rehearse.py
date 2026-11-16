#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""capstone-rehearse AC 用例集（规格 v2 §1，25 条 AC）。

只通过公开接口断言外部行为：`rehearse` / `render_report` / `main` /
`to_dict` 与三个可注入 adapter；不断言私有函数调用顺序（v2 §2）。
"""
import io
import json
import os
import re
import subprocess
import sys
import unittest
from contextlib import redirect_stderr, redirect_stdout

from tests._paths import ROOT  # noqa: E402
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from tools.report_exam._types import Fragment  # noqa: E402
from tools.report_exam.index import MemoryEvidenceSource  # noqa: E402
from tools.capstone_rehearse import (  # noqa: E402
    BLOCKING, NON_BLOCKING, SCHEMA_VERSION, EvidenceWriter, FixedClock,
    MemoryStageInventory, StageEvidence, rehearse, render_report,
    render_summary, stages_from_specs)
from tools.capstone_rehearse.cli import main  # noqa: E402

GATES = ("VG-1", "VG-2", "VG-3", "VG-4", "VG-5", "VG-6")
CLOSED_ALL = ("VG-2", "VG-3", "VG-4", "VG-5", "VG-6")


DRILL_RAW = (
    "### 步骤 cr-01\n\n"
    "#### 确切命令\n\n```bash\npython -m tools.capstone_rehearse --stdout\n```\n\n"
    "#### 关键输出\n\n```text\ncr-01 覆盖度矩阵: 9 行\n```\n\n"
    "#### 截图（访问证明）\n\n> 截图捕获钩子：`edge --headless=new`\n"
)


def _fragment(skill, complete=True):
    return Fragment(
        step_id="cr-01", target="drill-target",
        source_path="evidence/%s-drill/x.md" % skill,
        command="cmd" if complete else "", output="out" if complete else "",
        screenshot="shot.png" if complete else "",
        raw=DRILL_RAW if complete else "")


def _fragments():
    return [_fragment(stage.skill) for stage in stages_from_specs()]


class CountingSource:
    """包装既有 MemoryEvidenceSource，仅附加调用计数（复用既有 adapter）。"""

    def __init__(self, fragments):
        self._inner = MemoryEvidenceSource(fragments)
        self.calls = 0

    def iter_fragments(self):
        self.calls += 1
        return self._inner.iter_fragments()


def _result(inventory=None, clock=None, source=None, closed=None):
    return rehearse(inventory or MemoryStageInventory(),
                    clock or FixedClock(), source, closed)


class ACTests(unittest.TestCase):
    # ---- AC-01 / AC-02 ----
    def test_ac01_matrix_nine_rows_with_keys(self):
        result = _result()
        self.assertEqual(len(result.matrix), 9)
        for row in result.matrix:
            self.assertEqual(set(vars(row).keys()) if hasattr(row, "__dict__")
                             else {"stage_id", "skill", "ready", "evidence_chain"},
                             {"stage_id", "skill", "ready", "evidence_chain"})
        self.assertEqual(SCHEMA_VERSION, "1.0")

    def test_ac01_unready_rows_not_skipped(self):
        inv = MemoryStageInventory(evidence={"cr-04": StageEvidence(True, False, True, True)})
        result = _result(inventory=inv)
        self.assertEqual(len(result.matrix), 9)
        self.assertFalse([r for r in result.matrix if r.stage_id == "cr-04"][0].ready)

    def test_ac02_ready_four_way_conjunction(self):
        flags = [(False, True, True, True), (True, False, True, True),
                 (True, True, False, True), (True, True, True, False)]
        for i, combo in enumerate(flags):
            with self.subTest(missing=i):
                ev = StageEvidence(*combo)
                self.assertFalse(ev.ready)
                self.assertEqual(len(ev.missing()), 1)
        self.assertTrue(StageEvidence(True, True, True, True).ready)

    # ---- AC-03 ----
    def test_ac03_evidence_source_called_and_no_wider_criteria(self):
        source = CountingSource(_fragments())
        result = _result(source=source)
        self.assertEqual(source.calls, 1)
        self.assertTrue(all(row.evidence_chain for row in result.matrix))
        broken = CountingSource([_fragment(s.skill, complete=False)
                                 for s in stages_from_specs()])
        self.assertFalse(any(r.evidence_chain for r in _result(source=broken).matrix))

    # ---- AC-04 / AC-20 ----
    def test_ac04_and_ac20_report_source_anchors(self):
        text = render_report(_result())
        for anchor in ("GOVERNANCE.md#L141-L151", "GOVERNANCE.md#L165-L171",
                       "OSAI-Exam-Guide-snapshot.md#L68", "capstone-rehearse-canonical.md"):
            self.assertIn(anchor, text)

    # ---- AC-05 / AC-06 / AC-07 / AC-08 ----
    def test_ac05_timeline_segments_monotonic(self):
        result = _result()
        self.assertEqual(len(result.timeline), 5)  # 4 段 + 时间盒
        for slot in result.timeline[:4]:
            self.assertGreater(slot.duration, 0)
            self.assertAlmostEqual(slot.end - slot.start, slot.duration)
            self.assertTrue(slot.key_node)
        self.assertEqual([s.start for s in result.timeline[:4]], [0.0, 4.0, 16.0, 20.0])

    def test_ac06_decoy_timebox_and_overrun(self):
        normal = _result(clock=FixedClock({"decoy_timebox": 0.5}))
        self.assertFalse(any("超时" in c for c in normal.compression))
        over = _result(clock=FixedClock({"decoy_timebox": 0.6}))
        self.assertTrue(any("放弃理由" in c for c in over.compression))
        self.assertAlmostEqual(over.timeline[-1].duration, 0.6)

    def test_ac07_overtime_boundary_23_24_25(self):
        for hours, expected in ((23.0, False), (24.0, False), (25.0, True)):
            with self.subTest(hours=hours):
                result = _result(clock=FixedClock({"buffer": hours - 20.0}))
                self.assertEqual(result.overtime, expected)
                self.assertEqual(bool(result.compression), expected)

    def test_ac08_estimate_vs_measured(self):
        plain = _result()
        self.assertIsNone(plain.timeline[0].measured)
        self.assertIn("未实测", render_report(plain))
        measured = _result(clock=FixedClock(measured={"recon_foothold": 3.2}))
        self.assertAlmostEqual(measured.timeline[0].measured, 3.2)
        self.assertEqual(measured.timeline[0].estimate, 4.0)
        self.assertIn("3.2", render_report(measured))

    # ---- AC-09 / AC-10 / AC-16 ----
    def test_ac09_gaps_with_suggestions(self):
        inv = MemoryStageInventory(evidence={"cr-04": StageEvidence(True, False, True, True)})
        result = _result(inventory=inv)
        self.assertTrue(result.gaps)
        self.assertTrue(all(g.suggestion for g in result.gaps))

    def test_ac10_severity_two_values_exclusive(self):
        result = _result()
        allowed = {BLOCKING, NON_BLOCKING}
        self.assertTrue(all(g.severity in allowed for g in result.gaps))
        self.assertEqual(len(result.gaps), len(result.blocking) + len(result.non_blocking))
        self.assertFalse([g for g in result.blocking if g.severity == NON_BLOCKING])

    def test_ac16_unready_false_and_ready_path_reachable(self):
        self.assertFalse(_result().ready_for_exam)
        ready = _result(source=CountingSource(_fragments()), closed=CLOSED_ALL)
        self.assertTrue(ready.ready_for_exam)
        self.assertEqual(ready.pending, ())

    def test_ac16_no_real_exploitation_actions(self):
        pkg = os.path.join(ROOT, "tools", "capstone_rehearse")
        # evidence.py 的 subprocess 仅用于委托共享证据收集器，属合法证据生产端。
        for name in ("model.py", "inventory.py", "clock.py", "walk.py",
                     "report.py", "cli.py"):
            with open(os.path.join(pkg, name), encoding="utf-8") as handle:
                src = handle.read()
            for forbidden in ("subprocess", "socket", "requests", "urllib"):
                self.assertNotIn(forbidden, src, name)

    # ---- AC-11 / AC-12 / AC-13 / AC-14 ----
    def test_ac11_report_four_deliverables(self):
        text = render_report(_result())
        for heading in ("## 1. 覆盖度矩阵", "## 2. 24h 节奏时间线",
                        "## 3. 缺口与补强清单", "## 4. 演练结论",
                        "是否具备实战条件"):
            self.assertIn(heading, text)

    def test_ac12_report_references_paths_not_bodies(self):
        text = render_report(_result(), ["evidence/capstone-rehearse-drill/cr-01.md"])
        self.assertIn("evidence/capstone-rehearse-drill/cr-01.md", text)
        self.assertNotIn("cr-01 覆盖度矩阵: 9 行", text)

    def test_ac13_disclaimer_and_real_path_filtered(self):
        text = render_report(_result(), ["evidence/attack-rag-real/a.md"])
        self.assertIn("演练/仿真，非 OSAI 正式考试", text)
        self.assertNotIn("attack-rag-real", text)

    def test_ac14_no_verify_checks_impersonation(self):
        self.assertNotIn("checks", _result().to_dict())

    # ---- AC-15 / AC-17 / AC-18 ----
    def test_ac15_glossary_checker_passes(self):
        proc = subprocess.run([sys.executable, os.path.join(ROOT, "scripts", "check_glossary.py")],
                              capture_output=True, text=True, cwd=ROOT)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)

    def test_ac17_all_six_gates_listed_with_evidence_methods(self):
        """v2 AC-17：VG-1…VG-6 逐条列出且各带取证方式（VG-1 已关闭）。"""
        text = render_report(_result())
        for gate in GATES:
            self.assertIn(gate, text)
        self.assertIn("取证方式", text)
        self.assertIn("已关闭", text)

    def test_ac18_deterministic_double_run(self):
        first = json.dumps(_result().to_dict(), sort_keys=True, ensure_ascii=False)
        second = json.dumps(_result().to_dict(), sort_keys=True, ensure_ascii=False)
        self.assertEqual(first, second)

    # ---- AC-19 ----
    def test_ac19_cli_exit_codes_1_and_2(self):
        with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            self.assertEqual(main(["--stdout"]), 1)
            self.assertEqual(main(["--measured", "/definitely/missing.json"]), 2)
        self.assertIn("ready_for_exam", render_summary(_result()))

    # ---- AC-21 ----
    def test_ac21_evidence_writer_strict_and_ai_log(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            writer = EvidenceWriter(os.path.join(tmp, "drill"))
            path, code, err = writer.emit(
                "cr-01", "python -m tools.capstone_rehearse --stdout --step cr-01",
                "cr-01 覆盖度矩阵: 9 行", "矩阵", "shot-cmd")
            self.assertEqual(code, 0, err)
            with open(path, encoding="utf-8") as handle:
                text = handle.read()
            self.assertIn("#### AI 交互日志", text)
            self.assertIn("三件套齐全**：是", text)

    # ---- AC-23 / AC-24 / AC-25 ----
    def test_ac23_zero_pyrit_import(self):
        pkg = os.path.join(ROOT, "tools", "capstone_rehearse")
        for name in os.listdir(pkg):
            if name.endswith(".py"):
                with open(os.path.join(pkg, name), encoding="utf-8") as handle:
                    text = handle.read()
                self.assertNotRegex(text, r"^\s*(import pyrit|from pyrit)", name)

    def test_ac24_artifact_budget(self):
        proc = subprocess.run(
            [sys.executable, os.path.join(ROOT, "scripts", "check_token_budget.py"),
             "--artifact", "spec-v2", "docs/specs/capstone-rehearse-spec-v2.md"],
            capture_output=True, text=True, cwd=ROOT)
        self.assertEqual(proc.returncode, 0, proc.stdout)

    def test_ac25_v1_upstream_intact(self):
        with open(os.path.join(ROOT, "docs", "specs",
                               "capstone-rehearse-spec-v1.md"), encoding="utf-8") as handle:
            text = handle.read()
        self.assertEqual(len(re.findall(r"^## [1-7]\.", text, re.M)), 7)
        self.assertEqual(len(re.findall(r"^\d+\. As ", text, re.M)), 32)

    # ---- CLI 分支（覆盖率与端到端可复现） ----
    def test_cli_writes_out_and_report(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            out, rep = os.path.join(tmp, "r.json"), os.path.join(tmp, "r.md")
            with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
                self.assertEqual(main(["--out", out, "--report", rep]), 1)
            with open(out, encoding="utf-8") as handle:
                payload = json.load(handle)
            with open(rep, encoding="utf-8") as handle:
                report_text = handle.read()
            self.assertEqual(len(payload["matrix"]), 9)
            self.assertEqual(len(payload["gates"]), 6)
            self.assertIn("## 4. 演练结论", report_text)

    def test_cli_step_and_plain_summary(self):
        with redirect_stdout(io.StringIO()) as buf:
            self.assertEqual(main(["--stdout", "--step", "cr-03"]), 1)
        self.assertIn("cr-03", buf.getvalue())
        with redirect_stdout(io.StringIO()) as buf2:
            main([])
        self.assertIn("ready_for_exam", buf2.getvalue())

    def test_cli_invalid_evidence_dir(self):
        with redirect_stderr(io.StringIO()):
            self.assertEqual(main(["--evidence-dir", "/definitely/missing"]), 2)

    def test_cli_emit_evidence(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            target = os.path.join(tmp, "drill")
            with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
                self.assertEqual(main(["--emit-evidence", target]), 1)
            self.assertEqual(len([f for f in os.listdir(target)
                                  if f.endswith(".md")]), 6)

    def test_repo_inventory_real_paths(self):
        from tools.capstone_rehearse import RepoStageInventory
        inv = RepoStageInventory(ROOT)
        for stage in stages_from_specs():
            evidence = inv.evidence_for(stage.stage_id)
            self.assertIsInstance(evidence.ready, bool)
            self.assertIsInstance(evidence.missing(), tuple)

    def test_manifest_static_paths_exist(self):
        """回归护栏：清单内 tests/ 与实现落点均为仓库静态文件，迁移后不得失效。

        evidence/*-drill 为运行时产物，不在仓库内，故不纳入本断言。
        """
        from tools.capstone_rehearse.inventory import STAGE_SPECS
        for spec in STAGE_SPECS:
            stage_id, skills, impls, tests = spec[0], spec[4], spec[5], spec[6]
            for path in impls + tests:
                self.assertTrue(os.path.exists(os.path.join(ROOT, path)),
                                "%s 清单路径失效：%s" % (stage_id, path))
            for skill in skills:
                self.assertTrue(
                    os.path.exists(os.path.join(ROOT, "skills", skill, "SKILL.md")),
                    "%s 技能本体缺失：%s" % (stage_id, skill))


if __name__ == "__main__":
    unittest.main()
