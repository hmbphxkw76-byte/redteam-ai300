#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""工件层：JSON 读取、三类解析器、凭据指纹。"""
import json
import os
import tempfile
import unittest

from tools.foothold_ad import artifact


class LoadJsonTest(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp(prefix="fa_artifact_")

    def _write(self, name, text):
        path = os.path.join(self.dir, name)
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(text)
        return path

    def test_missing_file_raises(self):
        with self.assertRaises(artifact.ArtifactError):
            artifact.load_json(os.path.join(self.dir, "absent.json"))

    def test_invalid_json_raises(self):
        path = self._write("bad.json", "{not json")
        with self.assertRaises(artifact.ArtifactError):
            artifact.load_json(path)

    def test_valid_json_returns_payload(self):
        path = self._write("ok.json", json.dumps({"domain": "corp"}))
        self.assertEqual(artifact.load_json(path)["domain"], "corp")


class ParseDirectoryTest(unittest.TestCase):
    def test_list_payload_is_users(self):
        directory = artifact.parse_directory([
            {"name": "svc", "enabled": True, "spn": ["MSSQLSvc/db:1433"]},
        ])
        self.assertEqual(directory.users[0].name, "svc")
        self.assertEqual(directory.users[0].spn, ("MSSQLSvc/db:1433",))

    def test_bloodhound_properties_and_nested_aces(self):
        payload = {
            "domain": "megacorpone.ai",
            "data": [{
                "Properties": {"name": "alice", "enabled": True},
                "Aces": [{"Principal": "svc-sql", "Right": "DS-Replication-Get-Changes-All"}],
            }],
            "computers": ["DC01-ROOT"],
        }
        directory = artifact.parse_directory(payload)
        self.assertEqual(directory.users[0].name, "alice")
        self.assertTrue(directory.users[0].enabled)
        self.assertEqual(directory.aces[0].principal, "svc-sql")
        self.assertEqual(directory.aces[0].target, "alice")
        self.assertEqual(directory.computers, ("DC01-ROOT",))

    def test_groups_mapping_and_list(self):
        mapping = artifact.parse_directory({"groups": {"Domain Admins": ["alice"]}})
        self.assertEqual(mapping.groups["Domain Admins"], ("alice",))
        listed = artifact.parse_directory({"groups": [{"name": "Domain Admins", "members": ["bob"]}]})
        self.assertEqual(listed.groups["Domain Admins"], ("bob",))

    def test_ace_rights_list_and_missing_name(self):
        directory = artifact.parse_directory({
            "users": [{"name": ""}, {"name": "svc", "enabled": "yes", "member_of": "Domain Users"}],
            "aces": [{"principal": "svc", "rights": ["DS-Replication-Get-Changes", "GenericAll"]}],
        })
        self.assertEqual([u.name for u in directory.users], ["svc"])
        self.assertTrue(directory.users[0].enabled)
        self.assertEqual(len(directory.aces), 2)
        self.assertEqual(directory.users[0].member_of, ("Domain Users",))

    def test_non_mapping_item_raises(self):
        with self.assertRaises(artifact.ArtifactError):
            artifact.parse_directory({"users": [42]})

    def test_non_mapping_payload_raises(self):
        with self.assertRaises(artifact.ArtifactError):
            artifact.parse_directory("nope")

    def test_user_lookup_case_insensitive(self):
        directory = artifact.parse_directory([{"name": "Alice"}])
        self.assertIsNotNone(directory.user("alice"))
        self.assertIsNone(directory.user("bob"))


class ParseTemplatesAndTrustsTest(unittest.TestCase):
    def test_templates_from_mapping_and_list(self):
        tpls = artifact.parse_templates({"templates": [{
            "name": "VulnTpl", "enrollee_supplies_subject": "true",
            "ekus": ["Client Authentication"], "enrollment_rights": "Domain Users",
            "requires_manager_approval": "no", "http_enrollment": "true",
        }]})
        self.assertTrue(tpls[0].enrollee_supplies_subject)
        self.assertFalse(tpls[0].requires_manager_approval)
        self.assertTrue(tpls[0].http_enrollment)
        self.assertEqual(tpls[0].ekus, ("Client Authentication",))
        self.assertEqual(len(artifact.parse_templates([{"name": "A"}, {"noname": True}])), 1)

    def test_templates_invalid_type_raises(self):
        with self.assertRaises(artifact.ArtifactError):
            artifact.parse_templates("bad")

    def test_trusts_parse_and_skip_incomplete(self):
        trusts = artifact.parse_trusts([
            {"source": "dmz", "target": "dev", "direction": "Bidirectional", "sid_filtering": "false"},
            {"source": "only-source"},
        ])
        self.assertEqual(len(trusts), 1)
        self.assertEqual(trusts[0].direction, "bidirectional")
        self.assertFalse(trusts[0].sid_filtering)

    def test_trusts_invalid_type_raises(self):
        with self.assertRaises(artifact.ArtifactError):
            artifact.parse_trusts(3)


class FingerprintTest(unittest.TestCase):
    def test_fingerprint_hides_full_hash(self):
        secret = "0123456789abcdef0123456789abcdef"
        text = artifact.fingerprint_hash(secret)
        self.assertIn("NTLM:01234567", text)
        self.assertIn("len=32", text)
        self.assertNotIn(secret, text)

    def test_empty_hash_raises(self):
        with self.assertRaises(artifact.ArtifactError):
            artifact.fingerprint_hash("  ")


if __name__ == "__main__":
    unittest.main()
