#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""attack-supply-chain Ch9 B6 边界加固测试（AC-01..12）。"""
import os
import sys
import unittest
from types import SimpleNamespace

from tests._paths import ROOT  # noqa: E402
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from tools.attack_infra.command import CommandResult, FakeCommand  # noqa: E402
from tools.attack_supply_chain import ch9_boundary as b  # noqa: E402
from tools.attack_supply_chain import ch9_boundary_model as m  # noqa: E402
from tools.attack_supply_chain import ch9_boundary_evidence as ev  # noqa: E402
from tools.attack_supply_chain import ch9_boundary_runner as runner  # noqa: E402


def _ctx(**kwargs):
    base = dict(command=FakeCommand({}), timeout=5, out_dir=".")
    base.update(kwargs)
    return SimpleNamespace(**base)


class RouteTests(unittest.TestCase):
    def test_ac01_runtime_to_infra(self):
        v = b.classify("sidecar exec into shared request-queue volume")
        self.assertEqual(v["owner"], m.RUNTIME)
        self.assertIn("ch9_container.py#writable_shared_volume", v.transfer_to)

    def test_ac02_artifact_to_self(self):
        v = b.classify("poison model artifact in MinIO registry")
        self.assertEqual(v.owner, m.ARTIFACT)
        self.assertIn("poison_engine.py#poison_model", v.transfer_to)

    def test_ac03_ambiguous(self):
        v = b.classify("sidecar modifies model artifact")
        self.assertEqual(v.owner, m.ARTIFACT)
        self.assertEqual(v.confidence, "ambiguous")
        self.assertEqual(v.reason, "ambiguous")
        self.assertIn("ch9_container", v.transfer_to)

    def test_ac04_no_signal(self):
        v = b.classify("")
        self.assertEqual(v.owner, "")
        self.assertEqual(v.reason, "no_signal")
        self.assertEqual(v.transfer_to, "")

    def test_ac05_frozen_and_reasons(self):
        v = m.BoundaryVerdict("x", "", "no_signal", "none")
        with self.assertRaises(Exception):
            v.owner = m.ARTIFACT
        with self.assertRaises(ValueError):
            m.BoundaryVerdict("x", "bogus", "no_signal", "none")
        with self.assertRaises(ValueError):
            m.BoundaryVerdict("x", "", "bogus_reason", "none")

    def test_ac08_dict_shim(self):
        v = b.classify("model artifact")
        self.assertEqual(v["owner"], m.ARTIFACT)
        self.assertEqual(v.get("transfer_to"), m.TRANSFER_ARTIFACT)
        self.assertIsNone(v.get("missing"))


class EvidenceTests(unittest.TestCase):
    def test_ac06_argv_strict(self):
        v = b.classify("model artifact")
        argv = ev.build_evidence_argv(v, out_dir="o", target="h")
        for flag in ("--step", "--cmd", "--output", "--shot-cmd", "--out", "--strict", "--note"):
            self.assertIn(flag, argv)
        self.assertIn(os.path.join("tools", "collect_evidence.py"), argv[1])

    def test_ac06_strict_ok(self):
        v = b.classify("model artifact")
        cmd = FakeCommand({"python": CommandResult(code=0, stdout="ok")})
        ev.emit_strict_evidence(_ctx(command=cmd, out_dir="o"), v)
        self.assertTrue(v.evidence_ok)
        self.assertEqual(v.evidence_extra["exit_code"], 0)

    def test_ac06_strict_fail(self):
        v = b.classify("model artifact")
        cmd = FakeCommand({"python": CommandResult(code=1, stderr="strict: missing")})
        ev.emit_strict_evidence(_ctx(command=cmd), v)
        self.assertFalse(v.evidence_ok)
        self.assertIn("evidence_error", v.evidence_extra)

    def test_ac07_no_shell(self):
        with open(ev.__file__, encoding="utf-8") as f:
            self.assertNotIn("shell=True", f.read())
        argv = ev.build_evidence_argv(b.classify(""))
        self.assertIn("--strict", argv)


class RunnerTests(unittest.TestCase):
    def test_runner_two_observations(self):
        cmd = FakeCommand({"python": CommandResult(code=0, stdout="ok")})
        vs = runner.run_boundary(
            ["sidecar exec volume", "poison dataset"], _ctx(command=cmd))
        self.assertEqual(len(vs), 2)
        self.assertEqual(vs[0].owner, m.RUNTIME)
        self.assertEqual(vs[1].owner, m.ARTIFACT)
        self.assertTrue(all(v.evidence_ok for v in vs))

    def test_runner_empty(self):
        self.assertEqual(runner.run_boundary([], _ctx()), [])

    def test_runner_no_attach(self):
        vs = runner.run_boundary(["model"], _ctx(), attach=None)
        self.assertEqual(vs[0].evidence_path, "")


if __name__ == "__main__":
    unittest.main()
