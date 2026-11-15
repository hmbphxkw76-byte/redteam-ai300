"""reuse 切片测试（AC-05/06/15/16/18 + B7）。"""
import os
import unittest

from tools.tooling_automate import manifest as M
from tools.tooling_automate.reuse import (
    build_argv,
    build_collect_evidence_argv,
    build_validator_argv,
)

PKG_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def task(step="e-01", category="enum", cmd="echo x", kind=None):
    inputs = {"cmd": cmd}
    if kind is not None:
        inputs["kind"] = kind
    return M.Task(category=category, target="h1", step=step, inputs=inputs,
                  outputs={"evidence": "ev.md"}, trigger="t", classification="auto", raw={})


class ReuseTests(unittest.TestCase):
    def test_collect_evidence_strict(self):
        argv = build_collect_evidence_argv(task())
        self.assertIn("tools/collect_evidence.py", argv)
        self.assertIn("--step", argv)
        self.assertIn("--cmd", argv)
        self.assertIn("--strict", argv)

    def test_collect_evidence_no_strict(self):
        argv = build_collect_evidence_argv(task(), strict=False)
        self.assertNotIn("--strict", argv)

    def test_collect_evidence_requires_cmd(self):
        with self.assertRaises(M.UsageError):
            build_collect_evidence_argv(task(cmd=""))

    def test_validator_argv(self):
        for kind in ("anatomy", "glossary", "budget", "coverage"):
            self.assertIn("python", build_validator_argv(kind)[0])
        self.assertIn("--min", build_validator_argv("coverage"))
        with self.assertRaises(M.UsageError):
            build_validator_argv("nope")

    def test_build_argv_dispatch(self):
        self.assertIn("tools/collect_evidence.py", build_argv(task()))
        self.assertIn("scripts/validate_skill.py", build_argv(task(category="validate", kind="anatomy")))

    def test_no_pyrit_import(self):
        # B7：零 PyRIT 依赖
        import pathlib
        for f in pathlib.Path(PKG_DIR, "tools", "tooling_automate").rglob("*.py"):
            self.assertNotIn("pyrit", f.read_text(encoding="utf-8").lower())

    def test_no_third_party(self):
        import pathlib
        banned = ("import requests", "import httpx", "import pandas")
        for f in pathlib.Path(PKG_DIR, "tools", "tooling_automate").rglob("*.py"):
            text = f.read_text(encoding="utf-8")
            for b in banned:
                self.assertNotIn(b, text)


if __name__ == "__main__":
    unittest.main()
