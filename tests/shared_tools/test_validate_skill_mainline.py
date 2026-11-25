#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""主线留痕校验器单测（AC-11）：构造最小仓库树，验证 PASS/GAP 与孤儿规格发现。"""
import io
import os
import tempfile
import unittest
from contextlib import redirect_stdout

from scripts.validate_skill_mainline import main, scan


class MainlineValidatorTests(unittest.TestCase):
    def _build(self, root, with_pointer=True, with_specs=True, gates=10):
        d = os.path.join(root, "skills", "demo")
        os.makedirs(d)
        with open(os.path.join(d, "SKILL.md"), "w", encoding="utf-8") as f:
            f.write("# demo\n" + ("skill-mainline-workflow\n" if with_pointer else ""))
        if with_specs:
            for name in ("demo-spec-v1.md", "demo-spec-v2.md"):
                p = os.path.join(root, "docs", "specs")
                os.makedirs(p, exist_ok=True)
                open(os.path.join(p, name), "w", encoding="utf-8").close()
        ops = os.path.join(root, "docs", "operations")
        os.makedirs(ops, exist_ok=True)
        for i in range(2, 2 + gates):
            open(os.path.join(ops, "demo-gate-stage%d.md" % i), "w", encoding="utf-8").close()

    def test_detects_full_trace(self):
        with tempfile.TemporaryDirectory() as tmp:
            self._build(tmp)
            data = scan(tmp)
            self.assertTrue(data["ok"], data)
            self.assertEqual(data["root_specs"], [])

    def test_detects_missing_pointer_and_specs(self):
        with tempfile.TemporaryDirectory() as tmp:
            self._build(tmp, with_pointer=False, with_specs=False, gates=0)
            data = scan(tmp)
            self.assertFalse(data["ok"])
            gaps = "".join(data["skills"][0]["gaps"])
            self.assertIn("主线", gaps)
            self.assertIn("规格 v1", gaps)
            self.assertIn("阶段门禁记录", gaps)

    def test_detects_orphan_root_specs(self):
        with tempfile.TemporaryDirectory() as tmp:
            self._build(tmp)
            open(os.path.join(tmp, "spec-v1-demo.md"), "w", encoding="utf-8").close()
            data = scan(tmp)
            self.assertEqual(data["root_specs"], ["spec-v1-demo.md"])
            self.assertFalse(data["ok"])


    def test_cli_strict_exit_code(self):
        with tempfile.TemporaryDirectory() as tmp:
            self._build(tmp, with_pointer=False, with_specs=False, gates=0)
            open(os.path.join(tmp, "spec-v1-demo.md"), "w", encoding="utf-8").close()
            with redirect_stdout(io.StringIO()):
                self.assertEqual(main(["--root", tmp]), 0)
                self.assertEqual(main(["--root", tmp, "--strict"]), 1)


if __name__ == "__main__":
    unittest.main()
