#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""foothold-traditional Ch9 A3/C2 加固测试（AC-01..12）。"""
import os
import sys
import unittest
from types import SimpleNamespace

from tests._paths import ROOT  # noqa: E402
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from tools.attack_infra.command import CommandResult, FakeCommand  # noqa: E402
from tools.foothold_traditional import ch9_evidence as ev  # noqa: E402
from tools.foothold_traditional import ch9_model as m  # noqa: E402
from tools.foothold_traditional import ch9_runner as runner  # noqa: E402
from tools.foothold_traditional import ch9_entry as entry  # noqa: E402

LEAK = "AKIAEXAMPLEKEY1234567890"


def _ctx(**kwargs):
    base = dict(ssrf_response="", sudo_l_output="",
                command=FakeCommand({}), timeout=5, out_dir=".")
    base.update(kwargs)
    return SimpleNamespace(**base)


class ModelTests(unittest.TestCase):
    def test_ac07_five_values_and_reasons(self):
        self.assertEqual(len(m.OUTCOMES), 5)
        v = m.TriadVerdict("x", m.ABSENT, "none_found")
        self.assertIn(v.outcome, m.OUTCOMES)
        with self.assertRaises(ValueError):
            m.TriadVerdict("x", "UNKNOWN")
        with self.assertRaises(ValueError):
            m.TriadVerdict("x", m.ABSENT, "bogus_reason")

    def test_dict_compat_shim(self):
        """零回归：既有轻量版用 v['outcome'] / v.get('shot_cmd') 访问。"""
        v = m.TriadVerdict("trad-09", m.ABSENT, "none_found", "x", "pwd", "out", "shot")
        self.assertEqual(v["outcome"], m.ABSENT)
        self.assertEqual(v.get("shot_cmd"), "shot")
        self.assertIsNone(v.get("not_a_field"))

    def test_fingerprint_text(self):
        fp = m.Fingerprint("AWS_ACCESS_KEY_ID", len(LEAK), "ssrf-env")
        self.assertIn("AWS_ACCESS_KEY_ID", fp.as_text())
        self.assertNotIn(LEAK, fp.as_text())


class SsrfTests(unittest.TestCase):
    def test_ac01_three_fingerprints(self):
        resp = "AWS_ACCESS_KEY_ID=%s\nAWS_SECRET_ACCESS_KEY=SCR\nAWS_SESSION_TOKEN=TOK" % LEAK
        v = entry.ssrf_credential_entry(_ctx(ssrf_response=resp))
        self.assertIs(v.outcome, m.EXPOSED_NO_AUTH)
        self.assertEqual(len(v.fingerprints), 3)
        self.assertTrue(all(isinstance(f, m.Fingerprint) for f in v.fingerprints))

    def test_ac02_none_found(self):
        v = entry.ssrf_credential_entry(_ctx(ssrf_response="<html/>"))
        self.assertIs(v.outcome, m.ABSENT)
        self.assertEqual(v.reason, "none_found")

    def test_ac02_forbidden(self):
        v = entry.ssrf_credential_entry(_ctx(ssrf_response="AccessDenied"))
        self.assertIs(v.outcome, m.AUTH_REQUIRED)
        self.assertEqual(v.reason, "forbidden")

    def test_ac03_no_plaintext(self):
        v = entry.ssrf_credential_entry(_ctx(
            ssrf_response="AWS_SECRET_ACCESS_KEY=%s" % LEAK))
        self.assertNotIn(LEAK, v.output)
        for fp in v.fingerprints:
            self.assertNotIn(LEAK, fp.as_text())

    def test_ac03_quoted_values_no_bypass(self):
        """P-1 回归：双/单引号包裹的凭据值也须脱敏并产生指纹。"""
        for q in ('"', "'"):
            resp = "AWS_SECRET_ACCESS_KEY=%s%s%s" % (q, LEAK, q)
            v = entry.ssrf_credential_entry(_ctx(ssrf_response=resp))
            self.assertNotIn(LEAK, v.output)
            self.assertEqual(len(v.fingerprints), 1)
            self.assertEqual(v.fingerprints[0].length, len(LEAK))

    def test_ac04_verified_exploited(self):
        cmd = FakeCommand({"aws": CommandResult(
            code=0, stdout='{"Arn":"arn:aws:iam::1:user/x"}')})
        v = entry.ssrf_credential_entry(_ctx(
            ssrf_response="AWS_ACCESS_KEY_ID=%s" % LEAK,
            verify_credential=True, command=cmd))
        self.assertIs(v.outcome, m.EXPLOITED)

    def test_ac04_verify_no_arn_not_exploited(self):
        cmd = FakeCommand({"aws": CommandResult(code=1, stderr="denied")})
        v = entry.ssrf_credential_entry(_ctx(
            ssrf_response="AWS_ACCESS_KEY_ID=%s" % LEAK,
            verify_credential=True, command=cmd))
        self.assertIs(v.outcome, m.EXPOSED_NO_AUTH)


class GpuTests(unittest.TestCase):
    def test_ac05_wrappers(self):
        v = entry.gpu_foothold_entry(_ctx(
            sudo_l_output="User m may run: (root) NOPASSWD: /opt/tools/gpu-run.sh"))
        self.assertIs(v.outcome, m.EXPOSED_NO_AUTH)
        self.assertIn("/opt/tools/gpu-run.sh", v.wrappers)

    def test_ac06_no_nopasswd(self):
        v = entry.gpu_foothold_entry(_ctx(sudo_l_output="(root) ALL"))
        self.assertIs(v.outcome, m.ABSENT)
        self.assertEqual(v.reason, "none_found")

    def test_ac06_no_tool(self):
        v = entry.gpu_foothold_entry(_ctx(sudo_l_output="not found: sudo"))
        self.assertIs(v.outcome, m.ABSENT)
        self.assertEqual(v.reason, "no_tool")


class EvidenceTests(unittest.TestCase):
    def _verdict(self):
        return m.TriadVerdict("trad-09", m.EXPOSED_NO_AUTH, "",
                              "ok", "curl -s <URL>", "out", "screenshot --step trad-09")

    def test_ac08_build_argv_strict(self):
        argv = ev.build_evidence_argv(self._verdict(), out_dir="o", target="h")
        for flag in ("--step", "--cmd", "--output", "--shot-cmd", "--out", "--strict", "--target"):
            self.assertIn(flag, argv)
        self.assertIn("tools/collect_evidence.py".replace("/", os.sep), argv[1])

    def test_ac08_strict_ok(self):
        v = self._verdict()
        cmd = FakeCommand({"python": CommandResult(code=0, stdout="fragment")})
        ev.emit_strict_evidence(_ctx(command=cmd, out_dir="o"), v)
        self.assertTrue(v.evidence_ok)
        self.assertEqual(v.evidence_extra["exit_code"], 0)
        self.assertEqual(v.evidence_path, os.path.join("o", "trad-09.md"))

    def test_ac08_strict_fail(self):
        v = self._verdict()
        cmd = FakeCommand({"python": CommandResult(code=1, stderr="missing screenshot")})
        ev.emit_strict_evidence(_ctx(command=cmd), v)
        self.assertFalse(v.evidence_ok)
        self.assertIn("evidence_error", v.evidence_extra)

    def test_ac08_note_fingerprints(self):
        v = self._verdict()
        v.fingerprints = (m.Fingerprint("AWS_ACCESS_KEY_ID", 20, "ssrf-env"),)
        argv = ev.build_evidence_argv(v)
        self.assertIn("--note", argv)

    def test_ac09_no_shell_true(self):
        with open(ev.__file__, encoding="utf-8") as f:
            src = f.read()
        self.assertNotIn("shell=True", src)


class RunnerTests(unittest.TestCase):
    def test_runner_all_steps_with_evidence(self):
        cmd = FakeCommand({"python": CommandResult(code=0, stdout="ok")})
        ctx = _ctx(ssrf_response="AWS_ACCESS_KEY_ID=%s" % LEAK,
                   sudo_l_output="(root) NOPASSWD: /x", command=cmd)
        verdicts = runner.run_ch9(ctx)
        self.assertEqual(len(verdicts), 2)
        self.assertTrue(all(v.evidence_ok for v in verdicts))

    def test_runner_unknown_step(self):
        with self.assertRaises(ValueError):
            runner.run_ch9(_ctx(), step_ids=("trad-99",))

    def test_runner_no_attach(self):
        verdicts = runner.run_ch9(
            _ctx(ssrf_response="AWS_ACCESS_KEY_ID=%s" % LEAK),
            step_ids=("trad-09",), attach=None)
        self.assertEqual(verdicts[0].evidence_path, "")


if __name__ == "__main__":
    unittest.main()
