#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""适配器与证据落盘路径测试（S2 / 阶段 9 覆盖率收敛）。

通过向 `sys.modules` 注入最小 PyRIT 桩，验证 `RealPyRITBackend` 的延迟导入
契约与官方命名空间（不安装 pyrit、不连真实端点）；并覆盖真实证据发送、
AI 交互日志、flag 双通道、演示 CLI 等此前被测试替身跳过的分支。

仅依赖标准库。运行：python -m unittest discover -s tests
"""
import contextlib
import importlib
import io
import os
import sys
import tempfile
import types
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from tools.attack_ai_agent import demo, run_attack  # noqa: E402
from tools.attack_ai_agent.backends import (FakePyRITBackend, RealPyRITBackend,
                                            TargetResponse)  # noqa: E402
from tools.attack_ai_agent.paths import build_all_paths, build_path_a, build_path_b, build_path_c  # noqa: E402
from tools.attack_ai_agent.runner import (build_ai_log, emit_evidence,
                                          flag_payload, graph_for_step)  # noqa: E402
from tools.attack_ai_agent.steps import (FINAL_STEPS, PATH_STEPS, STEP_SPECS,
                                         steps_for_paths)  # noqa: E402


class _Stub:
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)


def _module(name, **attrs):
    mod = types.ModuleType(name)
    for key, value in attrs.items():
        setattr(mod, key, value)
    return mod


class FakePyRITModules:
    """上下文管理器：在 sys.modules 中临时注册 PyRIT v1.1.0 命名空间桩。"""

    NAMES = ("pyrit", "pyrit.prompt_target", "pyrit.score",
             "pyrit.executor", "pyrit.executor.attack",
             "pyrit.executor.workflow", "pyrit.converter",
             "pyrit.prompt_normalizer", "pyrit.setup",
             "pyrit.setup.initialization", "pyrit.memory")
    # 双模型命名空间占位值（仅用于延迟导入契约测试，不连真实端点）
    ENV_KEYS = ("OPENAI_CHAT_KEY", "OPENAI_CHAT_ENDPOINT", "OPENAI_CHAT_MODEL",
                "OPENAI_SCORER_KEY", "OPENAI_SCORER_ENDPOINT", "OPENAI_SCORER_MODEL")

    def __enter__(self):
        self.saved = {n: sys.modules.get(n) for n in self.NAMES}
        self.saved_env = {k: os.environ.get(k) for k in self.ENV_KEYS}
        for k in self.ENV_KEYS:
            os.environ.setdefault(k, "stub-value")
        target = _module("pyrit.prompt_target",
                         OpenAIChatTarget=_Stub, HTTPTarget=_Stub,
                         get_http_target_json_response_callback_function=lambda key: key)
        class JudgeStub(_Stub):
            @classmethod
            def from_question(cls, **kwargs):
                return cls(**kwargs)

        score = _module("pyrit.score", SubStringScorer=_Stub,
                        SelfAskTrueFalseScorer=JudgeStub, TrueFalseQuestion=_Stub)
        attack = _module("pyrit.executor.attack",
                         PromptSendingAttack=_Stub, RedTeamingAttack=_Stub,
                         AttackExecutor=_Stub, AttackConverterConfig=_Stub,
                         AttackAdversarialConfig=_Stub, AttackScoringConfig=_Stub)
        workflow = _module("pyrit.executor.workflow", XPIATestWorkflow=_Stub,
                           XPIAWorkflow=_Stub)
        pkg = _module("pyrit")
        setup = _module("pyrit.setup")
        setup.__path__ = []  # 标为 package，使 `from pyrit.setup.initialization import ...` 可解析

        async def _initialize_pyrit_async(**kwargs):
            return None

        initialization = _module("pyrit.setup.initialization",
                                 initialize_pyrit_async=_initialize_pyrit_async)
        sys.modules.update({
            "pyrit": pkg, "pyrit.prompt_target": target, "pyrit.score": score,
            "pyrit.executor": _module("pyrit.executor"),
            "pyrit.executor.attack": attack,
            "pyrit.executor.workflow": workflow,
            "pyrit.converter": _module("pyrit.converter"),
            "pyrit.prompt_normalizer": _module("pyrit.prompt_normalizer"),
            "pyrit.setup": setup,
            "pyrit.setup.initialization": initialization,
            "pyrit.memory": _module("pyrit.memory"),
        })
        return self

    def __exit__(self, *exc):
        for name, value in self.saved.items():
            if value is None:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = value
        for k, v in self.saved_env.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v


class AdapterTests(unittest.TestCase):
    def test_lazy_imports_use_official_modules(self):
        with FakePyRITModules():
            backend = RealPyRITBackend({"response_key": "answer"})
            # 双模型命名空间（2026-11-14）：断言完整公开字符串
            self.assertEqual(
                backend.describe(),
                "pyrit-1.1.0 (dual-model: attack=OPENAI_CHAT_*, "
                "scorer=OPENAI_SCORER_*)")
            self.assertIsNotNone(backend.make_target("objective"))
            self.assertIsNotNone(backend.make_target("scorer"))
            self.assertIsNotNone(backend.make_target("tool"))
            self.assertIsNotNone(backend.make_attack_side_llm())
            self.assertIsNotNone(backend.make_scorer("judge"))
            self.assertIsNotNone(backend.make_scorer("deterministic"))
            self.assertEqual(backend.make_memory(False), "InMemory")
            self.assertEqual(backend.make_memory(True), "SQLite")

    def test_real_execute_requires_live_endpoint(self):
        with self.assertRaises(RuntimeError):
            RealPyRITBackend().execute("aia-02", "objective")


class PathSpecTests(unittest.TestCase):
    def test_all_three_path_specs_are_well_formed(self):
        specs = build_all_paths()
        self.assertEqual([s.path_id for s in specs], ["A", "B", "C"])
        for spec in specs:
            self.assertTrue(spec.steps)
            self.assertTrue(spec.components)
            self.assertTrue(any(c.role == "攻击策略" for c in spec.components))

    def test_path_a_marks_b7_exception(self):
        self.assertTrue(build_path_a().b7_exception)
        self.assertFalse(build_path_b().b7_exception)
        self.assertFalse(build_path_c().b7_exception)

    def test_path_b_uses_persistent_sqlite(self):
        text = str(build_path_b().components)
        self.assertIn("SQLiteMemory", text)
        self.assertIn("SQLite", text)

    def test_path_c_uses_http_target(self):
        self.assertIn("HTTPTarget", str(build_path_c().components))

    def test_steps_for_paths_order(self):
        ids = [s.step_id for s in steps_for_paths(("A", "B", "C"))]
        self.assertEqual(ids, ["aia-%02d" % i for i in range(1, 13)])
        self.assertEqual([s.step_id for s in steps_for_paths(("B",))],
                         ["aia-05", "aia-06", "aia-07", "aia-11", "aia-12"])
        self.assertEqual(PATH_STEPS["A"][0].step_id, "aia-01")
        self.assertEqual([s.step_id for s in FINAL_STEPS], ["aia-11", "aia-12"])


class EvidenceEmissionTests(unittest.TestCase):
    def test_real_evidence_emission_writes_strict_fragment(self):
        spec = STEP_SPECS[1]
        response = TargetResponse("内部系统提示已泄露", "完全生效", True, True)
        graph = graph_for_step(spec.step_id)
        with tempfile.TemporaryDirectory() as tmp:
            path = emit_evidence(spec, response, "完全生效", graph, "10.0.0.5", tmp)
            self.assertTrue(os.path.isfile(path))
            with open(path, encoding="utf-8") as handle:
                text = handle.read()
            self.assertIn("**三件套齐全**：是。", text)
            self.assertIn("#### AI 交互日志", text)

    def test_strict_mode_rejects_incomplete_output(self):
        spec = STEP_SPECS[1]
        response = TargetResponse("", "未生效")
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(RuntimeError):
                emit_evidence(spec, response, "未生效",
                              graph_for_step(spec.step_id), "10.0.0.5", tmp)

    def test_ai_log_contains_four_required_fields(self):
        spec = STEP_SPECS[1]
        log = build_ai_log(spec, graph_for_step(spec.step_id),
                           TargetResponse("out", "完全生效", True, True), "完全生效")
        for field in ("prompt:", "model:", "output:", "adoption:"):
            self.assertIn(field, log)

    def test_flag_payload_only_for_flag_steps(self):
        response = TargetResponse("flag body", "完全生效", True, True)
        self.assertEqual(flag_payload(STEP_SPECS[1], response), "")
        for spec in (STEP_SPECS[10], STEP_SPECS[11]):
            text = flag_payload(spec, response)
            self.assertIn("whoami", text)
            self.assertIn("ai_vector.txt", text)


class DemoCliTests(unittest.TestCase):
    def test_demo_full_run(self):
        with tempfile.TemporaryDirectory() as tmp:
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                code = demo.main(["--evidence-dir", tmp, "--scenario", "effective"])
            self.assertEqual(code, 0)
            self.assertIn("步骤数：12", buf.getvalue())
            self.assertEqual(len([f for f in os.listdir(tmp) if f.endswith(".md")]), 12)

    def test_demo_single_step_and_exemptions(self):
        with tempfile.TemporaryDirectory() as tmp:
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                code = demo.main(["--evidence-dir", tmp, "--step", "aia-02",
                                  "--scenario", "refusal", "--no-memory", "--no-tools"])
            self.assertEqual(code, 0)
            self.assertIn("步骤数：1", buf.getvalue())
            self.assertIn("未生效", buf.getvalue())

    def test_run_attack_default_backend(self):
        with tempfile.TemporaryDirectory() as tmp:
            report = run_attack("x", step="aia-01", evidence_dir=tmp)
            self.assertEqual(report.backend, "fake-stdlib")
            self.assertEqual(tuple(report.objectives), ("x",))
            self.assertEqual(len(report.as_dict()["graphs"]), 3)
            self.assertEqual(report.levels(), ("完全生效",))


if __name__ == "__main__":
    unittest.main()
