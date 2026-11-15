#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""attack-supply-chain seam 行为测试（S2 / 覆盖率收敛）。

只断言外部行为（返回值、异常、注入点），不断言实现细节；重依赖全部以假后端替代。
仅依赖标准库。运行：python -m unittest discover -s tests -q
"""
import json
import os
import sys
import tempfile
import types
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from tools.attack_supply_chain import (FakePoisonBackend, STEP_IDS,
                                       ArtPoisonBackend, build_args,
                                       inject_build, inject_dependency,
                                       inject_pipeline, is_malicious_detected,
                                       load_assets, poison_dataset,
                                       poison_model, run, scan)  # noqa: E402


class ReconInputTests(unittest.TestCase):
    def _write(self, obj):
        fd, path = tempfile.mkstemp(suffix=".json")
        os.close(fd)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(obj, f)
        return path

    def test_valid_surface(self):
        path = self._write({"model_registries": ["hf"], "dependency_sources": ["pypi"],
                            "data_pipelines": ["etl"], "trust_boundaries": ["dmz"]})
        try:
            s = load_assets(path)
            self.assertEqual(s.model_registries, ("hf",))
            self.assertEqual(s.as_dict()["dependency_sources"], ["pypi"])
        finally:
            os.unlink(path)

    def test_missing_field_raises(self):
        path = self._write({"model_registries": []})
        try:
            with self.assertRaises(ValueError):
                load_assets(path)
        finally:
            os.unlink(path)

    def test_non_object_raises(self):
        path = self._write([1, 2])
        try:
            with self.assertRaises(ValueError):
                load_assets(path)
        finally:
            os.unlink(path)


class PoisonEngineTests(unittest.TestCase):
    def test_frac_validation(self):
        for bad in (0, -0.1, 1.5):
            with self.assertRaises(ValueError):
                poison_dataset("c", "T", "X", bad)

    def test_dataset_fake_backend(self):
        be = FakePoisonBackend()
        out = poison_dataset("corpus", "TRIG", "evil", 0.05, backend=be)
        self.assertEqual(out["injected"], 5)
        self.assertEqual(be.calls[0][0], "dataset")

    def test_model_fake_backend(self):
        be = FakePoisonBackend()
        out = poison_model("bert", "lora.safetensors", "TRIG", backend=be)
        self.assertEqual(out["adapter_out"], "lora.safetensors")
        self.assertEqual(be.calls[0][0], "model")

    def test_art_backend_requires_dependency_or_raises(self):
        # 未安装 art 应抛 ImportError；已安装则构造成功但投毒未接 estimator 抛 NotImplementedError。
        try:
            be = ArtPoisonBackend()
        except ImportError:
            return
        with self.assertRaises(NotImplementedError):
            be.poison_model("base", "a.safetensors", "T")

    def test_art_backend_wiring_with_fake_module(self):
        be = ArtPoisonBackend(art_module=types.ModuleType("art"))
        with self.assertRaises(NotImplementedError):
            be.poison_dataset("c", "T", "X", 0.1)
        with self.assertRaises(NotImplementedError):
            be.poison_model("b", "a", "T")


class ModelScanTests(unittest.TestCase):
    def test_malicious_detected(self):
        def runner(path):
            return 1, json.dumps({"issues": [{"severity": "high", "desc": "x"}]})
        r = scan("m.pkl", runner=runner)
        self.assertEqual(r.severity_max, "HIGH")
        self.assertTrue(is_malicious_detected(r))

    def test_clean(self):
        r = scan("m.safetensors", runner=lambda p: (0, '{"issues": []}'))
        self.assertTrue(r.is_clean())
        self.assertFalse(is_malicious_detected(r))

    def test_empty_and_skipped(self):
        r = scan("m", runner=lambda p: (0, ""))
        self.assertTrue(r.is_clean())
        r2 = scan("m", runner=lambda p: (0, json.dumps({"issues": [], "skipped": ["a.onnx"]})))
        self.assertEqual(r2.skipped, ["a.onnx"])


class InjectorTests(unittest.TestCase):
    def test_dependency(self):
        cfg = inject_dependency("https://pypi", "requests", "requests-evil")
        self.assertEqual(cfg.kind, "dependency")
        self.assertIn("requests-evil", cfg.expected_effect)

    def test_pipeline(self):
        cfg = inject_pipeline("etl", "preprocess", "flip")
        self.assertEqual(cfg.config["stage"], "preprocess")

    def test_build_writer(self):
        seen = []
        cfg = inject_build("ci", "os.system('id')", writer=seen.append)
        self.assertEqual(seen[0], cfg)
        self.assertEqual(cfg.kind, "build")


class EvidenceTests(unittest.TestCase):
    def test_build_args_strict_and_flag(self):
        args = build_args("sc-08", "whoami; id", "loot/sc-08.md", flag="F",
                          ai_log="log", target="host", strict=True)
        self.assertEqual(args[args.index("--step") + 1], "sc-08")
        self.assertIn("--strict", args)
        self.assertIn("--flag", args)
        self.assertIn("--ai-log", args)
        self.assertIn("--target", args)

    def test_emit_injected_runner(self):
        captured = {}

        def runner(args):
            captured["args"] = args
            return "ok"
        out = build_args("sc-07", "c", "o")
        self.assertIsNotNone(out)
        # emit 通过 build_args；用 runner 捕获
        from tools.attack_supply_chain import emit
        emit("sc-07", "c", "o", runner=runner)
        self.assertIn("--step", captured["args"])


class WorkflowTests(unittest.TestCase):
    def test_step_ids(self):
        self.assertEqual(len(STEP_IDS), 8)
        self.assertEqual(STEP_IDS[0], "sc-01")
        self.assertEqual(STEP_IDS[-1], "sc-08")

    def test_unknown_step(self):
        with self.assertRaises(ValueError):
            run("sc-99", {})

    def test_run_sc02_and_sc05(self):
        out = run("sc-02", {"data": "c", "trigger": "T", "target": "X",
                            "frac": 0.02, "backend": FakePoisonBackend()})
        self.assertEqual(out["injected"], 2)
        cfg = run("sc-05", {"index": "i", "pkg": "p", "malicious": "p-evil"})
        self.assertEqual(cfg.kind, "dependency")

    def test_run_all_steps(self):
        fd, path = tempfile.mkstemp(suffix=".json")
        os.close(fd)
        with open(path, "w", encoding="utf-8") as f:
            json.dump({"model_registries": [], "dependency_sources": [],
                       "data_pipelines": [], "trust_boundaries": []}, f)
        runner = lambda args: "ok"
        try:
            self.assertIsNotNone(run("sc-01", {"assets_path": path}))
            self.assertIsNotNone(run("sc-02", {"data": "c", "trigger": "T",
                                               "target": "X", "frac": 0.01,
                                               "backend": FakePoisonBackend()}))
            self.assertIsNotNone(run("sc-03", {"base": "b", "adapter_out": "a",
                                               "trigger": "T",
                                               "backend": FakePoisonBackend()}))
            self.assertEqual(run("sc-04", {"pipeline": "p", "inject": "f"}).kind, "pipeline")
            self.assertEqual(run("sc-06", {"build": "ci", "payload": "x"}).kind, "build")
            self.assertEqual(run("sc-07", {"cmd": "c", "out": "o", "runner": runner}), "ok")
            self.assertEqual(run("sc-08", {"cmd": "c", "out": "o", "runner": runner}), "ok")
        finally:
            os.unlink(path)


if __name__ == "__main__":
    unittest.main()
