#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""加固用例：schema 版本、损坏工件、畸形输入、未知枚举、确定性与快照。

对齐「无真实环境」下的最佳实践：任何无法判定的输入必须落到
`BLOCKED` / `UNDETERMINED`，不得被静默解读为安全或不安全。
"""
import json
import os
import tempfile
import unittest

from tools.foothold_ad import artifact
from tools.foothold_ad.analyze import adcs_risks, path_to_domain_admin
from tools.foothold_ad.artifact import Directory, DirectoryUser, Template
from tools.foothold_ad.model import ABSENT, BLOCKED, EXPLOITED, UNDETERMINED
from tools.foothold_ad.runner import run


def write(path, text):
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(text)


def write_json(path, payload):
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False)


DIRECTORY = {
    "domain": "megacorpone.ai",
    "users": [{"name": "svc-sql", "enabled": True, "spn": ["MSSQLSvc/db:1433"],
               "preauth_required": True, "member_of": ["Domain Users"]}],
}
TEMPLATES = {"templates": [{"name": "T", "enrollee_supplies_subject": False,
                            "ekus": ["Client Authentication"], "enrollment_rights": ["Domain Admins"],
                            "requires_manager_approval": True, "http_enrollment": False}]}
TRUSTS = {"trusts": [{"source": "a", "target": "b", "direction": "bidirectional",
                      "sid_filtering": True}]}


class SchemaTest(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp(prefix="fa_schema_")

    def test_supported_schema_runs_normally(self):
        write_json(os.path.join(self.dir, "directory.json"),
                   dict(DIRECTORY, schema_version="1.1"))
        write_json(os.path.join(self.dir, "templates.json"), dict(TEMPLATES, schema_version="1.1"))
        write_json(os.path.join(self.dir, "trusts.json"), dict(TRUSTS, schema_version="1.0"))
        report = run(self.dir)
        self.assertEqual(report.schema_errors, {})
        self.assertEqual(report.results["ad-02"].verdict, EXPLOITED)

    def test_unsupported_schema_is_undetermined(self):
        write_json(os.path.join(self.dir, "directory.json"),
                   dict(DIRECTORY, schema_version="2.0"))
        report = run(self.dir)
        self.assertIn("directory.json", report.schema_errors)
        self.assertEqual(report.results["ad-02"].verdict, UNDETERMINED)
        self.assertIn("schema_version", report.results["ad-02"].notes[0])
        self.assertNotIn("ad-02", report.blocked_steps)

    def test_missing_schema_is_tolerated(self):
        write_json(os.path.join(self.dir, "directory.json"), DIRECTORY)
        report = run(self.dir)
        self.assertEqual(report.schema_errors, {})
        self.assertEqual(report.results["ad-02"].verdict, EXPLOITED)


class CorruptArtifactTest(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp(prefix="fa_corrupt_")

    def _blocked(self, name, text):
        write(os.path.join(self.dir, name), text)
        report = run(self.dir)
        self.assertIn(name, report.parse_errors)
        self.assertIn(name, report.missing)
        self.assertTrue(report.results["ad-02"].verdict == BLOCKED
                        or report.results["ad-04"].verdict == BLOCKED)
        return report

    def test_empty_file_blocks(self):
        self._blocked("directory.json", "")

    def test_truncated_json_blocks(self):
        self._blocked("templates.json", '{"templates": [{"name": "T"')

    def test_non_utf8_blocks(self):
        path = os.path.join(self.dir, "trusts.json")
        with open(path, "wb") as handle:
            handle.write(b"\xff\xfe\x00bad")
        report = run(self.dir)
        self.assertIn("trusts.json", report.parse_errors)

    def test_deep_nesting_rejected(self):
        path = os.path.join(self.dir, "deep.json")
        write(path, "[" * 3000 + "]" * 3000)
        with self.assertRaises(artifact.ArtifactError):
            artifact.load_json(path)

    def test_oversized_rejected(self):
        path = os.path.join(self.dir, "big.json")
        write(path, json.dumps({"a": "x" * 200}))
        with self.assertRaises(artifact.ArtifactError):
            artifact.load_json(path, max_bytes=50)

    def test_missing_file_message(self):
        with self.assertRaises(artifact.ArtifactError):
            artifact.load_json(os.path.join(self.dir, "nope.json"))


class MalformedContentTest(unittest.TestCase):
    def test_unicode_homoglyph_is_distinct(self):
        directory = artifact.parse_directory({
            "users": [{"name": "alice", "member_of": ["Domain Admins"]},
                      {"name": "\u0430lice", "member_of": []}],
        })
        self.assertEqual(len(directory.users), 2)
        self.assertIsNotNone(directory.user("\u0430lice"))

    def test_cyclic_aces_terminate(self):
        directory = Directory("corp", users=(
            DirectoryUser("alice", member_of=("Helpdesk",)),
            DirectoryUser("bob", member_of=("Domain Admins",)),
        ), aces=())
        from tools.foothold_ad.artifact import Ace
        directory = Directory(directory.domain, directory.users,
                              aces=(Ace("Helpdesk", "GenericAll", "alice"),
                                    Ace("alice", "GenericAll", "Helpdesk")))
        self.assertEqual(path_to_domain_admin(directory, ("alice",)), ())

    def test_duplicate_principals_kept(self):
        directory = artifact.parse_directory({"aces": [
            {"principal": "svc", "right": "DS-Replication-Get-Changes-All", "target": "DC=corp"},
            {"principal": "svc", "right": "DS-Replication-Get-Changes-All", "target": "DC=corp"},
        ]})
        self.assertEqual(len(directory.aces), 2)

    def test_type_mismatch_is_tolerated(self):
        directory = artifact.parse_directory({"users": [
            {"name": "svc", "enabled": ["yes"], "spn": 5, "preauth_required": "maybe"},
        ]})
        user = directory.users[0]
        self.assertIsNone(user.enabled)
        self.assertIsNone(user.preauth_required)
        self.assertEqual(user.spn, ("5",))


class UnknownEnumTest(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp(prefix="fa_enum_")

    def test_unknown_trust_direction_not_safe(self):
        write_json(os.path.join(self.dir, "directory.json"), DIRECTORY)
        write_json(os.path.join(self.dir, "trusts.json"),
                   {"trusts": [{"source": "a", "target": "b", "direction": "sideways",
                                "sid_filtering": True}]})
        report = run(self.dir)
        self.assertEqual(report.results["ad-06"].verdict, UNDETERMINED)
        self.assertTrue(any("信任方向" in note for note in report.results["ad-06"].notes))

    def test_unknown_delegation_noted(self):
        payload = {"domain": "corp", "users": [
            {"name": "svc", "enabled": True, "spn": [], "preauth_required": True,
             "delegation": "kcd-v2"}]}
        write_json(os.path.join(self.dir, "directory.json"), payload)
        report = run(self.dir)
        self.assertTrue(any("委派取值未知" in note for note in report.results["ad-02"].notes))

    def test_esc1_requires_both_issuance_guards(self):
        hits, unknown = adcs_risks((Template("T", True, ("Client Authentication",),
                                             ("Domain Users",), False, False, None, None),))
        self.assertEqual(hits, ())
        self.assertTrue(any("授权签名" in item for item in unknown))

    def test_esc8_requires_epa_disabled(self):
        hits, _ = adcs_risks((Template("T", False, (), (), True, True, None, True),))
        self.assertEqual(hits, ())
        hits, _ = adcs_risks((Template("T", False, (), (), True, True, None, False),))
        self.assertEqual([f.kind for f in hits], ["esc8"])

    def test_template_missing_epa_is_undetermined(self):
        hits, unknown = adcs_risks((Template("T", False, (), (), True, True, None, None),))
        self.assertEqual(hits, ())
        self.assertTrue(any("EPA" in item for item in unknown))


class DeterminismTest(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp(prefix="fa_det_")

    def _write(self, reverse=False):
        for name, payload in (("directory.json", DIRECTORY), ("templates.json", TEMPLATES),
                              ("trusts.json", TRUSTS)):
            body = dict(reversed(list(payload.items()))) if reverse else payload
            write_json(os.path.join(self.dir, name), body)

    def test_same_input_same_digest(self):
        self._write()
        first = run(self.dir).digest()
        second = run(self.dir).digest()
        self.assertEqual(first, second)
        self.assertEqual(len(first), 64)

    def test_key_order_does_not_change_digest(self):
        self._write()
        first = run(self.dir).digest()
        self._write(reverse=True)
        self.assertEqual(first, run(self.dir).digest())

    def test_digest_changes_with_input(self):
        self._write()
        first = run(self.dir).digest()
        write_json(os.path.join(self.dir, "templates.json"), {"templates": []})
        self.assertNotEqual(first, run(self.dir).digest())


if __name__ == "__main__":
    unittest.main()
