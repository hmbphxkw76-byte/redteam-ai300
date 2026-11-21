#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Ch6 增量 CLI 入口测试（AC-C11 可 copy/paste 复现；Stage 10 H2 修复）。

两层验证：
  1. subprocess 实跑 8 个 `-m` 命令（外部行为：退出码 + JSON 输出）；
  2. 进程内调用各模块 `_main()`（让 trace 覆盖率计入 CLI 分支；mock sys.argv）。
不断言内部算法。
"""
import importlib
import json
import os
import subprocess
import sys
import tempfile
import unittest

from tests._paths import ROOT  # noqa: E402

MODULES = [
    ("exporter", ["--store", "X", "--out", "./export"]),
    ("fingerprint", ["--dim", "384"]),
    ("probing", ["--vec", "dummy"]),
    ("triage", ["--vec", "dummy", "--top", "10"]),
    ("slotfill", ["--vec", "dummy"]),
    ("beamsearch", ["--vec", "dummy"]),
    ("decision", ["--model-known", "--time-tight"]),
    ("envelope", ["--capability", "ALGEN", "--no-lab"]),
]


class Ch6CliTests(unittest.TestCase):
    def test_all_eight_cli_commands_reproducible(self):
        for mod, extra in MODULES:
            with self.subTest(module=mod):
                argv = list(extra)
                if mod == "exporter":
                    argv = ["--store", "X", "--out",
                            os.path.join(tempfile.gettempdir(), "ch6_cli_export")]
                proc = subprocess.run(
                    [sys.executable, "-m", "tools.attack_embeddings." + mod] + argv,
                    cwd=str(ROOT), capture_output=True, text=True, timeout=30)
                self.assertEqual(proc.returncode, 0,
                                 "%s 非零退出：%s" % (mod, proc.stderr[-200:]))
                self.assertIn('"step"', proc.stdout,
                              "%s 未输出结构化 JSON" % mod)
                start = proc.stdout.find("{")
                payload = json.loads(proc.stdout[start:])
                self.assertTrue(str(payload.get("step", "")).startswith("emb-c"),
                                "%s step 标记缺失" % mod)

    def test_inprocess_main_covers_cli_branches(self):
        """进程内调用 _main()，使 trace 覆盖率计入 CLI 分支。"""
        old_argv = sys.argv
        try:
            for mod, extra in MODULES:
                with self.subTest(module=mod):
                    argv = list(extra)
                    if mod == "exporter":
                        argv = ["--store", "X", "--out",
                                os.path.join(tempfile.gettempdir(), "ch6_cov_export")]
                    sys.argv = ["prog"] + argv
                    m = importlib.import_module("tools.attack_embeddings." + mod)
                    rc = m._main()
                    self.assertEqual(rc, 0, "%s._main() 非零" % mod)
        finally:
            sys.argv = old_argv


if __name__ == "__main__":
    unittest.main()
