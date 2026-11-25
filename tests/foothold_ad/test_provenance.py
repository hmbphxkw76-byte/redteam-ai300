#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""来源与完整性：清单缺失、哈希不符、字段缺失、登记但文件缺失。"""
import json
import os
import tempfile
import unittest

from tools.foothold_ad import provenance


def write_json(path, payload):
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False)


class ProvenanceTest(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp(prefix="fa_prov_")
        self.artifact = os.path.join(self.dir, "directory.json")
        write_json(self.artifact, {"domain": "corp", "users": []})

    def _manifest(self, **overrides):
        entry = {
            "file": "directory.json",
            "sha256": provenance.sha256_file(self.artifact),
            "source": "bloodhound-python",
            "tool_version": "1.8.0",
            "captured_at": "2026-11-25T10:00:00Z",
            "operator": "tester",
        }
        entry.update(overrides)
        write_json(os.path.join(self.dir, provenance.MANIFEST_FILE), {"artifacts": [entry]})

    def test_sha256_is_stable(self):
        self.assertEqual(provenance.sha256_file(self.artifact),
                         provenance.sha256_file(self.artifact))
        self.assertEqual(len(provenance.sha256_file(self.artifact)), 64)

    def test_missing_manifest_marks_untrusted(self):
        report = provenance.verify(self.dir)
        self.assertFalse(report.ok)
        self.assertFalse(report.manifest_found)
        self.assertIn("directory.json", report.untrusted)
        self.assertTrue(any("artifact_manifest.json" in note for note in report.notes))

    def test_complete_manifest_passes(self):
        self._manifest()
        report = provenance.verify(self.dir)
        self.assertTrue(report.ok, report.to_dict())
        self.assertEqual(report.untrusted, ())
        self.assertTrue(report.entries[0].ok)

    def test_tampered_file_is_untrusted(self):
        self._manifest()
        write_json(self.artifact, {"domain": "corp", "users": [{"name": "evil"}]})
        report = provenance.verify(self.dir)
        self.assertFalse(report.ok)
        self.assertIn("directory.json", report.untrusted)
        problems = report.entries[0].problems
        self.assertTrue(any("sha256" in item for item in problems))

    def test_missing_field_is_untrusted(self):
        self._manifest(operator="")
        report = provenance.verify(self.dir)
        self.assertFalse(report.ok)
        self.assertTrue(any("operator" in item for item in report.entries[0].problems))

    def test_manifest_entry_without_file(self):
        self._manifest()
        write_json(os.path.join(self.dir, provenance.MANIFEST_FILE), {"artifacts": [{
            "file": "trusts.json", "sha256": "0" * 64, "source": "nltest",
            "tool_version": "10.0", "captured_at": "2026-11-25T10:00:00Z", "operator": "tester",
        }]})
        report = provenance.verify(self.dir, files=("directory.json", "trusts.json"))
        self.assertFalse(report.ok)
        self.assertIn("trusts.json", report.missing_files)
        self.assertIn("directory.json", report.untrusted)

    def test_manifest_mapping_form(self):
        sha = provenance.sha256_file(self.artifact)
        write_json(os.path.join(self.dir, provenance.MANIFEST_FILE), {
            "directory.json": {"sha256": sha, "source": "ldapsearch",
                               "tool_version": "2.5", "captured_at": "2026-11-25",
                               "operator": "tester"},
        })
        report = provenance.verify(self.dir, files=("directory.json",))
        self.assertTrue(report.ok, report.to_dict())

    def test_unreadable_manifest(self):
        with open(os.path.join(self.dir, provenance.MANIFEST_FILE), "w", encoding="utf-8") as handle:
            handle.write("{broken")
        report = provenance.verify(self.dir)
        self.assertFalse(report.ok)
        self.assertTrue(report.notes)

    def test_empty_manifest_table(self):
        write_json(os.path.join(self.dir, provenance.MANIFEST_FILE), {"artifacts": []})
        report = provenance.verify(self.dir)
        self.assertFalse(report.ok)
        self.assertIn("directory.json", report.untrusted)


class CliVerifyTest(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp(prefix="fa_prov_cli_")
        self.artifact = os.path.join(self.dir, "directory.json")
        write_json(self.artifact, {"domain": "corp"})
        write_json(os.path.join(self.dir, provenance.MANIFEST_FILE), {"artifacts": [{
            "file": "directory.json", "sha256": provenance.sha256_file(self.artifact),
            "source": "bloodhound-python", "tool_version": "1.8.0",
            "captured_at": "2026-11-25T10:00:00Z", "operator": "tester",
        }]})

    def _run(self, argv):
        import contextlib
        import io
        from tools.foothold_ad import cli
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = cli.main(argv)
        return code, out.getvalue()

    def test_verify_exit_zero_for_complete_artifacts(self):
        code, out = self._run(["verify", "--artifacts", self.dir])
        self.assertEqual(code, 0, out)
        self.assertIn('"ok": true', out)

    def test_verify_exit_one_for_tampered_artifacts(self):
        write_json(self.artifact, {"domain": "corp", "users": [{"name": "evil"}]})
        code, out = self._run(["verify", "--artifacts", self.dir])
        self.assertEqual(code, 1)
        self.assertIn("directory.json", out)


if __name__ == "__main__":
    unittest.main()
