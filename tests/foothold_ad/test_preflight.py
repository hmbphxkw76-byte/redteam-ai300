#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""无环境前置清单：缺失/已存在状态、采集命令与字段、CLI 两种输出。"""
import contextlib
import io
import json
import os
import tempfile
import unittest

from tools.foothold_ad import cli, preflight


class PreflightTest(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp(prefix="fa_pre_")

    def test_all_missing(self):
        payload = preflight.build(self.dir)
        self.assertEqual(len(payload["missing"]), 5)
        self.assertEqual(payload["present"], [])
        self.assertFalse(payload["provenance"]["manifest_present"])
        self.assertTrue(all(item["commands"] for item in payload["plan"]))
        self.assertIn("verify", payload["next"])

    def test_present_artifact_status_and_steps(self):
        with open(os.path.join(self.dir, "directory.json"), "w", encoding="utf-8") as handle:
            handle.write("{}")
        payload = preflight.build(self.dir)
        entry = [item for item in payload["plan"] if item["file"] == "directory.json"][0]
        self.assertEqual(entry["status"], "present")
        self.assertIn("ad-02", entry["steps"])
        self.assertIn("directory.json", payload["present"])

    def test_render_lists_commands_fields_and_provenance(self):
        text = preflight.render(preflight.build(self.dir))
        self.assertIn("采集:", text)
        self.assertIn("字段:", text)
        self.assertIn("artifact_manifest.json", text)
        self.assertIn("缺失", text)

    def test_render_skips_present_optional_artifacts(self):
        for name in ("tickets.json", "proof.json"):
            with open(os.path.join(self.dir, name), "w", encoding="utf-8") as handle:
                handle.write("{}")
        text = preflight.render(preflight.build(self.dir))
        self.assertNotIn("tickets.json [present]", text)

    def test_cli_preflight_json_and_text(self):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = cli.main(["preflight", "--artifacts", self.dir, "--json"])
        self.assertEqual(code, 0)
        self.assertIn("plan", json.loads(out.getvalue()))

        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = cli.main(["preflight", "--artifacts", self.dir])
        self.assertEqual(code, 0)
        self.assertIn("工件目录", out.getvalue())


if __name__ == "__main__":
    unittest.main()
