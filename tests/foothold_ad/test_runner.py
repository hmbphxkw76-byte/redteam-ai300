#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""编排层：工件读取、缺件 BLOCKED、步骤子集与结论序列化。"""
import json
import os
import tempfile
import unittest
from unittest import mock

from tools.foothold_ad import runner
from tools.foothold_ad.model import BLOCKED, EXPLOITED, UNDETERMINED, StepResult


def write(dir_path, name, payload):
    path = os.path.join(dir_path, name)
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False)
    return path


DIRECTORY = {
    "domain": "megacorpone.ai",
    "users": [
        {"name": "svc-sql", "domain": "megacorpone.ai", "enabled": True,
         "spn": ["MSSQLSvc/db01:1433"], "preauth_required": True, "member_of": ["Domain Users"]},
        {"name": "alice", "domain": "dev.megacorpone.ai", "enabled": True,
         "preauth_required": True, "member_of": ["Domain Admins"]},
    ],
    "aces": [{"principal": "svc-sql", "right": "DS-Replication-Get-Changes-All", "target": "DC=megacorpone"}],
}
TEMPLATES = {"templates": [{"name": "VulnTpl", "enrollee_supplies_subject": True,
                            "ekus": ["Client Authentication"], "enrollment_rights": ["Domain Users"],
                            "requires_manager_approval": False, "http_enrollment": True,
                            "authorized_signatures_required": False, "epa_enabled": False}]}
TRUSTS = {"trusts": [{"source": "dmz", "target": "dev", "direction": "bidirectional",
                      "sid_filtering": False}]}


class RunnerTest(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp(prefix="fa_runner_")

    def _full(self):
        write(self.dir, "directory.json", DIRECTORY)
        write(self.dir, "templates.json", TEMPLATES)
        write(self.dir, "trusts.json", TRUSTS)

    def test_full_run_reports_all_steps(self):
        self._full()
        report = runner.run(self.dir, owned=("svc-sql",))
        self.assertEqual(report.loaded, ("directory.json", "templates.json", "trusts.json"))
        self.assertEqual(report.missing, ())
        self.assertEqual(report.blocked_steps, ())
        self.assertEqual(report.results["ad-02"].verdict, EXPLOITED)
        self.assertIn("ad-01", report.to_dict()["steps"][0]["step_id"])
        self.assertEqual(report.to_dict()["steps"][0]["step_id"], "ad-01")

    def test_missing_artifacts_block_dependent_steps(self):
        report = runner.run(self.dir)
        self.assertEqual(report.loaded, ())
        self.assertEqual(set(report.blocked_steps), {"ad-01", "ad-02", "ad-04", "ad-05", "ad-06"})
        self.assertIn("directory.json", report.results["ad-02"].notes[0])
        self.assertEqual(report.results["ad-03"].verdict, UNDETERMINED)
        self.assertEqual(report.results["ad-08"].verdict, UNDETERMINED)

    def test_partial_artifacts_only_block_related_steps(self):
        write(self.dir, "directory.json", DIRECTORY)
        report = runner.run(self.dir)
        self.assertIn("ad-04", report.blocked_steps)
        self.assertIn("ad-01", report.blocked_steps)
        self.assertNotIn("ad-02", report.blocked_steps)
        self.assertEqual(report.results["ad-02"].verdict, EXPLOITED)

    def test_step_subset_and_command_filled(self):
        self._full()
        report = runner.run(self.dir, steps=("ad-04",))
        self.assertEqual(list(report.results), ["ad-04"])
        self.assertTrue(report.results["ad-04"].command)

    def test_tickets_and_proof_artifacts(self):
        self._full()
        write(self.dir, "tickets.json", [{"account": "svc-sql", "enctype": "rc4"}])
        write(self.dir, "proof.json", {"value": "flag{dc}", "panel": "flag{dc}"})
        report = runner.run(self.dir)
        self.assertEqual(report.results["ad-03"].verdict, EXPLOITED)
        self.assertEqual(report.results["ad-07"].verdict, EXPLOITED)

    def test_non_list_tickets_and_non_mapping_proof_ignored(self):
        self._full()
        write(self.dir, "tickets.json", {"account": "x"})
        write(self.dir, "proof.json", ["flag"])
        report = runner.run(self.dir)
        self.assertEqual(report.results["ad-03"].verdict, UNDETERMINED)
        self.assertEqual(report.results["ad-07"].verdict, UNDETERMINED)

    def test_undetermined_without_notes_gets_default_note(self):
        self._full()
        with mock.patch.object(runner, "assess", return_value={
            step: StepResult(step, UNDETERMINED) for step in runner.STEP_IDS
        }):
            report = runner.run(self.dir)
        self.assertEqual(report.results["ad-01"].notes, ("工件不足以判定",))

    def test_plan_steps_rejects_unknown(self):
        with self.assertRaises(ValueError):
            runner.plan_steps(("ad-01", "ad-99"))

    def test_plan_steps_defaults_and_orders(self):
        self.assertEqual(runner.plan_steps(), runner.STEP_IDS)
        self.assertEqual(runner.plan_steps(("ad-05", "ad-01")), ("ad-01", "ad-05"))
        self.assertEqual(runner.plan_steps(("",)), runner.STEP_IDS)


class BlockedOverrideTest(unittest.TestCase):
    def test_existing_blocked_is_preserved(self):
        dir_path = tempfile.mkdtemp(prefix="fa_blocked_")
        with mock.patch.object(runner, "assess", return_value={
            step: StepResult(step, BLOCKED, notes=("已阻断",)) for step in runner.STEP_IDS
        }):
            report = runner.run(dir_path)
        self.assertEqual(report.results["ad-01"].notes, ("已阻断",))


if __name__ == "__main__":
    unittest.main()
