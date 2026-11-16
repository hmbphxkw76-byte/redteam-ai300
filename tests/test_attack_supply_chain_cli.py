#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""attack-supply-chain SKILL.md CLI 入口测试（sc-02~sc-06）。

校验 SKILL.md 列出的 5 个独立工具脚本存在、可执行、参数契约与文档一致。
只断言外部行为（stdout JSON / 异常），仅依赖标准库。
运行：python -m unittest discover -s tests -q
"""
import contextlib
import importlib
import io
import json
import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

TOOLS = ("dataset_poison", "model_poison", "pipeline_poison",
         "dep_poison", "trigger_poison")


def _run(mod_name, argv):
    mod = importlib.import_module("tools." + mod_name)
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        code = mod.main(argv)
    return code, json.loads(buf.getvalue())


class SupplyChainCliTests(unittest.TestCase):
    def test_all_skill_tools_are_importable(self):
        for name in TOOLS:
            path = os.path.join(ROOT, "tools", name + ".py")
            self.assertTrue(os.path.isfile(path), "缺少 SKILL.md 工具: %s" % path)
            self.assertTrue(hasattr(importlib.import_module("tools." + name), "main"))

    def test_dataset_poison_inject_split(self):
        code, out = _run("dataset_poison",
                         ["--data", "corpus", "--inject", "TRIG:evil", "--frac", "0.05"])
        self.assertEqual(code, 0)
        self.assertEqual(out["trigger"], "TRIG")
        self.assertEqual(out["target"], "evil")
        self.assertEqual(out["injected"], 5)

    def test_dataset_poison_no_target(self):
        _, out = _run("dataset_poison", ["--data", "c", "--inject", "TRIG"])
        self.assertEqual(out["target"], "")

    def test_dataset_poison_bad_frac_raises(self):
        with self.assertRaises(ValueError):
            _run("dataset_poison", ["--data", "c", "--inject", "T:X", "--frac", "0"])

    def test_model_poison(self):
        code, out = _run("model_poison",
                         ["--base", "bert", "--adapter-out", "lora.safetensors",
                          "--trigger", "T"])
        self.assertEqual(code, 0)
        self.assertEqual(out["adapter_out"], "lora.safetensors")

    def test_pipeline_poison(self):
        code, out = _run("pipeline_poison",
                         ["--pipeline", "etl", "--stage", "preprocess", "--inject", "flip"])
        self.assertEqual(code, 0)
        self.assertEqual(out["kind"], "pipeline")
        self.assertEqual(out["config"]["stage"], "preprocess")

    def test_dep_poison(self):
        code, out = _run("dep_poison",
                         ["--index", "https://pypi", "--pkg", "requests",
                          "--malicious", "requests-evil"])
        self.assertEqual(code, 0)
        self.assertEqual(out["kind"], "dependency")
        self.assertIn("requests-evil", out["expected_effect"])

    def test_trigger_poison(self):
        code, out = _run("trigger_poison",
                         ["--build", "ci", "--payload", "import os; os.system('id')"])
        self.assertEqual(code, 0)
        self.assertEqual(out["kind"], "build")


if __name__ == "__main__":
    unittest.main()
