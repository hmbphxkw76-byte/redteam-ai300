#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""CLI 层：子命令、输出落盘、退出码。"""
import contextlib
import io
import json
import os
import tempfile
import unittest

from tools.foothold_ad import cli
from tests.foothold_ad.test_runner import DIRECTORY, TEMPLATES, TRUSTS, write


def run_cli(argv):
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = cli.main(argv)
    return code, out.getvalue(), err.getvalue()


class CliTest(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp(prefix="fa_cli_")

    def _full(self):
        write(self.dir, "directory.json", DIRECTORY)
        write(self.dir, "templates.json", TEMPLATES)
        write(self.dir, "trusts.json", TRUSTS)

    def test_plan_lists_eight_steps(self):
        code, out, _ = run_cli(["plan"])
        self.assertEqual(code, 0)
        self.assertEqual(len(out.strip().splitlines()), 8)

    def test_analyze_stdout_json(self):
        self._full()
        code, out, _ = run_cli(["analyze", "--artifacts", self.dir, "--steps", "ad-02,ad-04",
                                "--owned", "svc-sql"])
        self.assertEqual(code, 0)
        payload = json.loads(out)
        self.assertEqual([s["step_id"] for s in payload["steps"]], ["ad-02", "ad-04"])
        self.assertEqual(payload["blocked_steps"], [])

    def test_analyze_writes_out_file_and_evidence_argv(self):
        self._full()
        target = os.path.join(self.dir, "out.json")
        code, out, _ = run_cli(["analyze", "--artifacts", self.dir, "--out", target,
                                "--evidence-argv", "--steps", "ad-07"])
        self.assertEqual(code, 0)
        self.assertEqual(out, "")
        with open(target, encoding="utf-8") as handle:
            payload = json.load(handle)
        self.assertIn("evidence_argv", payload)
        self.assertIn("--strict", payload["evidence_argv"]["ad-07"])

    def test_unknown_step_exits_two(self):
        code, _, err = run_cli(["analyze", "--artifacts", self.dir, "--steps", "ad-99"])
        self.assertEqual(code, 2)
        self.assertIn("未知步骤", err)

    def test_missing_artifacts_exits_one(self):
        code, out, _ = run_cli(["analyze", "--artifacts", self.dir])
        self.assertEqual(code, 1)
        self.assertTrue(json.loads(out)["missing"])

    def test_no_subcommand_prints_usage(self):
        code, _, _ = run_cli([])
        self.assertEqual(code, 2)


if __name__ == "__main__":
    unittest.main()
