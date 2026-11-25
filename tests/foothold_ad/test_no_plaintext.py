#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""凭据不落盘：完整哈希不得出现在结论或证据参数中（P-1 约束）。"""
import json
import os
import tempfile
import unittest

from tools.foothold_ad import artifact
from tools.foothold_ad.evidence import build_evidence_argv
from tools.foothold_ad.runner import run

SECRET = "0123456789abcdef0123456789abcdef"
SECRET2 = "fedcba9876543210fedcba9876543210"


class NoPlaintextTest(unittest.TestCase):
    def test_report_omits_hashes(self):
        dir_path = tempfile.mkdtemp(prefix="fa_secret_")
        payload = {
            "domain": "corp",
            "users": [{"name": "svc", "enabled": True, "spn": ["HTTP/svc"],
                       "ntlm": SECRET, "password": "P@ssw0rd!"}],
            "aces": [{"principal": "svc", "right": "DS-Replication-Get-Changes-All",
                      "target": "DC=corp", "hash": SECRET2}],
        }
        with open(os.path.join(dir_path, "directory.json"), "w", encoding="utf-8") as handle:
            json.dump(payload, handle)
        text = json.dumps(run(dir_path).to_dict(), ensure_ascii=False)
        self.assertNotIn(SECRET, text)
        self.assertNotIn(SECRET2, text)
        self.assertNotIn("P@ssw0rd!", text)

    def test_evidence_argv_omits_hashes(self):
        dir_path = tempfile.mkdtemp(prefix="fa_secret_ev_")
        with open(os.path.join(dir_path, "directory.json"), "w", encoding="utf-8") as handle:
            json.dump({"domain": "corp", "users": [{"name": "svc", "enabled": True,
                                                   "spn": ["HTTP/svc"], "ntlm": SECRET}]}, handle)
        report = run(dir_path, steps=("ad-02",))
        argv = build_evidence_argv(report.results["ad-02"])
        self.assertNotIn(SECRET, " ".join(argv))

    def test_fingerprint_is_the_only_hash_form(self):
        text = artifact.fingerprint_hash(SECRET)
        self.assertEqual(text, "NTLM:01234567(len=32)")
        self.assertNotIn(SECRET, text)


if __name__ == "__main__":
    unittest.main()
