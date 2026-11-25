# -*- coding: utf-8 -*-
"""阶段9：新模块 CLI 进程内覆盖测试（Ch6 经验：CLI 须 _main 进程内调用才计入覆盖率）。"""
import contextlib
import importlib
import io
import json
import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)

MODULES = ("mcp_backdoor", "pickle_rce", "format_matrix", "amplification",
           "adapter_poison", "tokenizer_swap", "pickle_bypass", "stealth_backdoor",
           "ch8_evasion", "surface_fields", "ch8_steps", "alignment")

ARGV = {
    "mcp_backdoor": ["--server", "s", "--helper", "list_all", "--author", "a", "--email", "e"],
    "pickle_rce": ["--base", "resnet18", "--epoch", "99", "--files", "resnet18_epoch_015.pt"],
    "format_matrix": [],
    "amplification": ["--samples", "3", "--base", "74", "--factor", "10"],
    "adapter_poison": ["--ip", "192.0.2.1", "--text", "host 192.0.2.10"],
    "tokenizer_swap": ["--vocab", "/v.json", "--fast", "/t.json"],
    "pickle_bypass": ["--list"],
    "stealth_backdoor": ["--encode", "import sys"],
    "ch8_evasion": [],
    "surface_fields": [],
    "ch8_steps": ["--list"],
    "alignment": [],
}


class TestCh8CliCoverage(unittest.TestCase):
    def test_all_modules_have_main(self):
        for name in MODULES:
            mod = importlib.import_module("tools.attack_supply_chain." + name)
            self.assertTrue(callable(getattr(mod, "main", None)), name)

    def test_cli_inprocess(self):
        for name in MODULES:
            mod = importlib.import_module("tools.attack_supply_chain." + name)
            buf = io.StringIO()
            old_argv = sys.argv
            try:
                sys.argv = ["python -m " + name] + ARGV[name]
                import inspect
                params = inspect.signature(mod.main).parameters
                with contextlib.redirect_stdout(buf):
                    code = mod.main(ARGV[name]) if params else mod.main()
            finally:
                sys.argv = old_argv
            self.assertEqual(code, 0, name)
            self.assertTrue(buf.getvalue().strip(), name)


if __name__ == "__main__":
    unittest.main()
