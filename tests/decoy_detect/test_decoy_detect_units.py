#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""decoy-detect 单元测试（S2）：三维度特征、时间盒、判定策略、清单、
质量门、编排与 CLI 外部行为。

对应 v2 AC1–AC9。仅依赖标准库；只测外部行为，不断言实现细节。
运行：python -m unittest discover -s tests -t .
"""
import contextlib
import io
import json
import os
import sys
import tempfile
import unittest

from tests._paths import ROOT  # noqa: E402
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from tools.decoy_detect import cli, features, listgen, model, policy, runner, validate  # noqa: E402
from tools.decoy_detect.model import (Dimension, DecoyJudgment,  # noqa: E402
                                      HostSignals, JudgmentConclusion)
from tools.decoy_detect.timebox import TimeBoxTracker  # noqa: E402

FIXTURE = os.path.join(ROOT, "tests", "fixtures", "decoy_scan.json")
FIXED_TS = "2026-01-01T00:00:00+08:00"


def _judgment(**overrides):
    base = dict(host_id="h", hit_dimensions=[Dimension.BEHAVIOR],
                evidence={Dimension.BEHAVIOR.value: "x"},
                abandonment_reason="r", conclusion=JudgmentConclusion.DECOY,
                timestamp=FIXED_TS)
    base.update(overrides)
    return DecoyJudgment(**base)


class ModelTests(unittest.TestCase):
    def test_judgment_fields_constant(self):
        self.assertEqual(model.JUDGMENT_FIELDS,
                         ("host_id", "hit_dimensions", "evidence",
                          "abandonment_reason", "timestamp"))

    def test_missing_fields_all_present(self):
        self.assertEqual(_judgment().missing_fields(), [])

    def test_missing_fields_partial(self):
        j = DecoyJudgment(host_id="", timestamp="")
        miss = j.missing_fields()
        self.assertIn("host_id", miss)
        self.assertIn("hit_dimensions", miss)
        self.assertIn("evidence", miss)
        self.assertIn("abandonment_reason", miss)
        self.assertIn("timestamp", miss)

    def test_to_dict_roundtrip(self):
        data = _judgment().to_dict()
        self.assertEqual(data["host_id"], "h")
        self.assertEqual(data["hit_dimensions"], [Dimension.BEHAVIOR.value])
        self.assertEqual(data["conclusion"], JudgmentConclusion.DECOY.value)

    def _write(self, payload):
        fd, path = tempfile.mkstemp(suffix=".json")
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            if isinstance(payload, str):
                f.write(payload)
            else:
                json.dump(payload, f)
        self.addCleanup(os.remove, path)
        return path

    def test_load_scan_valid(self):
        path = self._write({"expected_decoys": 2, "hosts": [{"host_id": "a"}]})
        scan = model.load_scan(path)
        self.assertEqual(scan.expected_decoys, 2)
        self.assertEqual(len(scan.hosts), 1)

    def test_load_scan_missing_file_raises(self):
        with self.assertRaises(ValueError):
            model.load_scan(os.path.join(ROOT, "tests", "no_such_file.json"))

    def test_load_scan_bad_json_raises(self):
        with self.assertRaises(ValueError):
            model.load_scan(self._write("{not json"))

    def test_load_scan_not_dict_raises(self):
        with self.assertRaises(ValueError):
            model.load_scan(self._write([1, 2, 3]))

    def test_load_scan_empty_hosts_raises(self):
        with self.assertRaises(ValueError):
            model.load_scan(self._write({"hosts": []}))

    def test_load_scan_bad_expected_raises(self):
        with self.assertRaises(ValueError):
            model.load_scan(self._write({"expected_decoys": "x", "hosts": [{}]}))

    def test_coerce_host(self):
        self.assertEqual(model.coerce_host({"a": 1}), {"a": 1})
        self.assertEqual(model.coerce_host(None), {})


class FeatureTests(unittest.TestCase):
    def test_extract_full(self):
        sig = features.extract({
            "host_id": "h1", "present_categories": ["LLM引擎"],
            "decoy_suspected": False, "high_value_service": True,
            "reachable_entry": True, "exploitable_misconfig": True,
            "banner_service_count": 3, "info_sufficient": True,
            "inventory_match": True, "decoy_reason": "",
        })
        self.assertTrue(sig.ai_surface_present)
        self.assertEqual(sig.host_id, "h1")

    def test_extract_empty_defaults(self):
        sig = features.extract({})
        self.assertEqual(sig.host_id, "unknown")
        self.assertFalse(sig.ai_surface_present)  # present_categories 空

    def test_extract_non_dict(self):
        sig = features.extract(None)
        self.assertEqual(sig.host_id, "unknown")

    def test_extract_bad_banner(self):
        sig = features.extract({"banner_service_count": "x"})
        self.assertEqual(sig.banner_service_count, 1)

    def test_extract_target_fallback(self):
        sig = features.extract({"target": "10.0.0.9"})
        self.assertEqual(sig.host_id, "10.0.0.9")

    def test_classify_behavior_only(self):
        sig = HostSignals(host_id="h", ai_surface_present=False)
        self.assertEqual(features.classify_dimensions(sig), [Dimension.BEHAVIOR])

    def test_classify_all_three(self):
        sig = HostSignals(host_id="h", ai_surface_present=False,
                          high_value_service=False, reachable_entry=False,
                          exploitable_misconfig=False, banner_service_count=0)
        self.assertEqual(features.classify_dimensions(sig),
                         [Dimension.BEHAVIOR, Dimension.LEAK_MISSING, Dimension.NO_VALUE])

    def test_classify_none(self):
        sig = HostSignals(host_id="h")
        self.assertEqual(features.classify_dimensions(sig), [])

    def test_classify_leak_requires_all_three(self):
        sig = HostSignals(host_id="h", high_value_service=False)  # 仅一项缺失
        self.assertNotIn(Dimension.LEAK_MISSING, features.classify_dimensions(sig))

    def test_classify_no_value_variants(self):
        for overrides in ({"banner_service_count": 0},
                          {"info_sufficient": False},
                          {"inventory_match": False}):
            sig = HostSignals(host_id="h", **overrides)
            self.assertIn(Dimension.NO_VALUE, features.classify_dimensions(sig))

    def test_explain(self):
        sig = HostSignals(host_id="h", ai_surface_present=False,
                          decoy_reason="0/7 类指纹",
                          high_value_service=False, reachable_entry=False,
                          exploitable_misconfig=False, banner_service_count=0,
                          info_sufficient=False, inventory_match=False)
        reasons = features.explain(sig)
        self.assertIn(Dimension.BEHAVIOR.value, reasons)
        self.assertIn("0/7 类指纹", reasons[Dimension.BEHAVIOR.value])
        self.assertIn(Dimension.NO_VALUE.value, reasons)


class TimeBoxTests(unittest.TestCase):
    def test_record_elapsed(self):
        t = TimeBoxTracker()
        self.assertEqual(t.record("h", 600), 600)
        self.assertEqual(t.elapsed("h"), 600)

    def test_exceeded(self):
        t = TimeBoxTracker(limit_seconds=1800)
        t.record("h", 2000)
        self.assertTrue(t.exceeded("h"))

    def test_start_stop_with_clock(self):
        ticks = iter([100.0, 250.0])
        t = TimeBoxTracker(limit_seconds=100, clock=lambda: next(ticks))
        t.start("h")
        self.assertEqual(t.stop("h"), 150.0)
        self.assertTrue(t.exceeded("h"))

    def test_stop_without_start(self):
        t = TimeBoxTracker()
        self.assertEqual(t.stop("h"), 0.0)

    def test_elapsed_unrecorded(self):
        t = TimeBoxTracker()
        self.assertEqual(t.elapsed("h"), 0.0)

    def test_record_bad_value(self):
        t = TimeBoxTracker()
        self.assertEqual(t.record("h", "bad"), 0.0)

    def test_exceeded_custom_limit(self):
        t = TimeBoxTracker(limit_seconds=1800)
        t.record("h", 500)
        self.assertTrue(t.exceeded("h", limit_seconds=100))


class PolicyTests(unittest.TestCase):
    def test_two_dims_decoy(self):
        self.assertEqual(policy.decide([Dimension.BEHAVIOR, Dimension.NO_VALUE]),
                         JudgmentConclusion.DECOY)

    def test_one_dim_cross_validated_decoy(self):
        self.assertEqual(policy.decide([Dimension.BEHAVIOR], cross_validated=True),
                         JudgmentConclusion.DECOY)

    def test_one_dim_no_cross_uncertain(self):
        self.assertEqual(policy.decide([Dimension.BEHAVIOR]),
                         JudgmentConclusion.UNCERTAIN_ABANDONED)

    def test_one_dim_threat_model_decoy(self):
        self.assertEqual(policy.decide([Dimension.BEHAVIOR], threat_model_decoy=True),
                         JudgmentConclusion.DECOY)

    def test_zero_dim_scored(self):
        self.assertEqual(policy.decide([]), JudgmentConclusion.SCORED)

    def test_zero_dim_threat_cross_uncertain(self):
        self.assertEqual(
            policy.decide([], cross_validated=True, threat_model_decoy=True),
            JudgmentConclusion.UNCERTAIN_ABANDONED)

    def test_abandonment_reason_variants(self):
        self.assertEqual(policy.abandonment_reason(JudgmentConclusion.SCORED, [], False), "")
        two = [Dimension.BEHAVIOR, Dimension.NO_VALUE]
        self.assertIn("诱饵", policy.abandonment_reason(JudgmentConclusion.DECOY, two, False))
        self.assertIn("时间盒", policy.abandonment_reason(
            JudgmentConclusion.UNCERTAIN_ABANDONED, two, True))
        self.assertIn("单维度", policy.abandonment_reason(
            JudgmentConclusion.UNCERTAIN_ABANDONED, [Dimension.BEHAVIOR], False))
        self.assertIn("threat-model", policy.abandonment_reason(
            JudgmentConclusion.UNCERTAIN_ABANDONED, [], False))


class ListGenTests(unittest.TestCase):
    def test_render_basic(self):
        md = listgen.render_markdown(
            [_judgment(host_id="10.0.0.1",
                       hit_dimensions=[Dimension.BEHAVIOR, Dimension.NO_VALUE])])
        for header in ("主机标识", "命中维度", "具体依据", "放弃理由", "时间戳", "结论"):
            self.assertIn(header, md)
        self.assertIn("10.0.0.1", md)

    def test_render_empty(self):
        md = listgen.render_markdown([])
        self.assertIn("判定条目", md)
        self.assertIn("（无）", md)

    def test_render_mismatch_warning(self):
        md = listgen.render_markdown([_judgment()], expected_decoys=2)
        self.assertIn("告警", md)

    def test_render_match(self):
        md = listgen.render_markdown([_judgment()], expected_decoys=1)
        self.assertIn("数量与预期一致", md)


class ValidateTests(unittest.TestCase):
    def test_missing_fields_violation(self):
        v = validate.validate_quality_gate([_judgment(evidence={})])
        self.assertTrue(any("缺字段" in x for x in v))

    def test_single_dim_decoy_violation(self):
        v = validate.validate_quality_gate(
            [_judgment(conclusion=JudgmentConclusion.DECOY, cross_validated=False)])
        self.assertTrue(any("未经交叉验证" in x for x in v))

    def test_single_dim_scored_violation(self):
        v = validate.validate_quality_gate(
            [_judgment(conclusion=JudgmentConclusion.SCORED, cross_validated=False)])
        self.assertTrue(any("静默判为计分目标" in x for x in v))

    def test_over_timebox_unmarked(self):
        v = validate.validate_quality_gate(
            [_judgment(hit_dimensions=[Dimension.BEHAVIOR, Dimension.NO_VALUE],
                       elapsed_seconds=3000, timebox_exceeded=False)])
        self.assertTrue(any("未标记 timebox_exceeded" in x for x in v))

    def test_over_timebox_wrong_conclusion(self):
        v = validate.validate_quality_gate(
            [_judgment(hit_dimensions=[Dimension.BEHAVIOR, Dimension.NO_VALUE],
                       elapsed_seconds=3000, timebox_exceeded=True,
                       conclusion=JudgmentConclusion.DECOY)])
        self.assertTrue(any("未按「不确定-已放弃」处置" in x for x in v))

    def test_valid_no_violation(self):
        j = _judgment(hit_dimensions=[Dimension.BEHAVIOR, Dimension.NO_VALUE])
        self.assertEqual(validate.validate_quality_gate([j]), [])

    def test_has_decoys(self):
        self.assertTrue(validate.has_decoys([_judgment()]))
        self.assertFalse(validate.has_decoys(
            [_judgment(conclusion=JudgmentConclusion.UNCERTAIN_ABANDONED)]))


class RunnerTests(unittest.TestCase):
    def test_run_scan_fixture(self):
        scan = model.load_scan(FIXTURE)
        report = runner.run_scan(scan, timestamp_fn=lambda: FIXED_TS)
        self.assertEqual(report.decoy_count, 2)
        self.assertEqual(report.uncertain_count, 2)
        self.assertEqual(report.scored_count, 1)
        self.assertTrue(report.passed, report.violations)
        self.assertTrue(report.to_dict()["count_matches"])
        # 超时主机会被强制为不确定-已放弃
        over = [j for j in report.judgments if j.host_id == "10.10.10.9"][0]
        self.assertTrue(over.timebox_exceeded)
        self.assertEqual(over.conclusion, JudgmentConclusion.UNCERTAIN_ABANDONED)


class CliTests(unittest.TestCase):
    def _tmp_scan(self, hosts):
        fd, path = tempfile.mkstemp(suffix=".json")
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump({"expected_decoys": 2, "hosts": hosts}, f)
        self.addCleanup(os.remove, path)
        return path

    def test_cli_run_stdout(self):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            code = cli.main(["run", "--inventory", FIXTURE])
        self.assertEqual(code, 0)
        self.assertIn("诱饵判定清单", buf.getvalue())

    def test_cli_run_out_file(self):
        with tempfile.TemporaryDirectory() as d:
            out = os.path.join(d, "judgment.md")
            with contextlib.redirect_stdout(io.StringIO()):
                code = cli.main(["run", "--inventory", FIXTURE, "--out", out])
            self.assertEqual(code, 0)
            with open(out, encoding="utf-8") as f:
                self.assertIn("诱饵判定清单", f.read())

    def test_cli_run_json(self):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            code = cli.main(["run", "--inventory", FIXTURE, "--out", "-", "--json"])
        self.assertEqual(code, 0)
        self.assertIn("\"decoy_count\": 2", buf.getvalue())

    def test_cli_bad_inventory_exit2(self):
        with contextlib.redirect_stderr(io.StringIO()):
            code = cli.main(["run", "--inventory",
                             os.path.join(ROOT, "tests", "nope.json")])
        self.assertEqual(code, 2)

    def test_cli_prefix_run(self):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            code = cli.main(["--inventory", FIXTURE])
        self.assertEqual(code, 0)

    def test_cli_help(self):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            self.assertEqual(cli.main(["-h"]), 0)
            self.assertEqual(cli.main([]), 2)

    def test_cli_evidence_dir(self):
        with tempfile.TemporaryDirectory() as d:
            shot = os.path.join(d, "shot.png")
            with open(shot, "wb") as f:
                f.write(b"\x89PNG\r\n\x1a\n")
            scan = self._tmp_scan([
                {"host_id": "h1", "present_categories": [],
                 "high_value_service": False, "reachable_entry": False,
                 "exploitable_misconfig": False, "banner_service_count": 0,
                 "info_sufficient": False, "inventory_match": False,
                 "elapsed_seconds": 300, "screenshot": shot},
            ])
            ev = os.path.join(d, "ev")
            man = os.path.join(d, "manifest.jsonl")
            md = os.path.join(d, "j.md")
            with contextlib.redirect_stdout(io.StringIO()):
                code = cli.main(["run", "--inventory", scan, "--out", md,
                                 "--evidence-dir", ev, "--manifest", man,
                                 "--strict-evidence"])
            self.assertEqual(code, 0)
            self.assertTrue(os.path.isfile(os.path.join(ev, "decoy-01.md")))
            self.assertTrue(os.path.isfile(man))


if __name__ == "__main__":
    unittest.main()
