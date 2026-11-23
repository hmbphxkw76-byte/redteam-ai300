#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""attack-jailbreak 外部行为测试（S2 / 阶段 9）。

仅标准库。通过 sys.modules 注入最小 PyRIT 桩验证 RealPyRITBackend 延迟导入
契约与官方 1.1.0 命名空间（不安装 pyrit / 不连端点）。覆盖规格 v2 的
AC-01/02/07/08/09/11/12/14/15/17/18/20。

运行：python -m unittest discover -s tests -t .
"""
import importlib
import os
import sys
import types
import unittest

from tests._paths import ROOT

if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from tools.attack_jailbreak.backends import (BackendFactory, FakePyRITBackend,
                                             RealPyRITBackend, TargetResponse,
                                             get_backend)
from tools.attack_jailbreak.runner import grade, run_steps, summary
from tools.attack_jailbreak.steps import (FINAL_STEPS, PATH_STEPS, PREFIX,
                                          STEP_IDS, STEP_SPECS, steps_for_paths)


class TestSteps(unittest.TestCase):
    def test_prefix_and_count(self):
        self.assertEqual(PREFIX, "jailbreak")
        self.assertEqual(len(STEP_IDS), 10)
        self.assertEqual(len(set(STEP_IDS)), 10)

    def test_all_ids_prefixed(self):
        for sid in STEP_IDS:
            self.assertTrue(sid.startswith("jailbreak-"), sid)

    def test_steps_for_paths_order(self):
        got = [s.step_id for s in steps_for_paths(["A", "B"])]
        self.assertEqual(got[:2], ["jailbreak-01", "jailbreak-02"])
        self.assertEqual(got[-2:], ["jailbreak-09", "jailbreak-10"])

    def test_evidence_hooks_present(self):
        for s in STEP_SPECS:
            self.assertIn("demo.py --step", s.command)
            self.assertIn("evidence/", s.screenshot_hook)


class TestGrading(unittest.TestCase):
    def test_deterministic_hit_success_without_llm(self):
        r = TargetResponse("ok", "完全生效", deterministic_hit=True)
        self.assertEqual(grade(r), "success")

    def test_partial_not_overstated(self):
        r = TargetResponse("partial", "部分生效", deterministic_hit=True)
        self.assertEqual(grade(r), "部分生效")

    def test_undetermined_preserved(self):
        r = TargetResponse("?", "UNDETERMINED")
        self.assertEqual(grade(r), "UNDETERMINED")

    def test_llm_only(self):
        r = TargetResponse("?", "完全生效", llm_hit=True)
        self.assertEqual(grade(r), "llm_hit")

    def test_no_hit_not_effective(self):
        r = TargetResponse("no", "完全生效")
        self.assertEqual(grade(r), "未生效")


class TestFakeBackend(unittest.TestCase):
    def test_is_backend_factory(self):
        self.assertIsInstance(FakePyRITBackend(), BackendFactory)

    def test_deterministic_output(self):
        a = run_steps(step_ids=["jailbreak-01", "jailbreak-08"], backend=FakePyRITBackend())
        b = run_steps(step_ids=["jailbreak-01", "jailbreak-08"], backend=FakePyRITBackend())
        self.assertEqual([r.evidence["grade"] for r in a],
                         [r.evidence["grade"] for r in b])

    def test_calls_recorded(self):
        be = FakePyRITBackend()
        run_steps(step_ids=["jailbreak-02"], backend=be)
        self.assertEqual(be.calls, [("jailbreak-02", be.calls[0][1])])

    def test_undetermined_scenario(self):
        results = run_steps(step_ids=["jailbreak-08"],
                            backend=FakePyRITBackend(scenario="undetermined"))
        self.assertEqual(results[0].evidence["grade"], "UNDETERMINED")

    def test_summary_counts(self):
        results = run_steps(step_ids=["jailbreak-01", "jailbreak-08"],
                            backend=FakePyRITBackend())
        s = summary(results)
        self.assertEqual(s["total"], 2)
        self.assertEqual(sum(s["grades"].values()), 2)

    def test_factory_default_fake(self):
        self.assertIsInstance(get_backend(), FakePyRITBackend)


class TestRealBackendStubbed(unittest.TestCase):
    """注入最小 pyrit 桩，验证延迟导入与 1.1.0 命名空间（B7）。"""

    def setUp(self):
        self.saved = {}
        mods = {
            "pyrit": types.ModuleType("pyrit"),
            "pyrit.executor": types.ModuleType("pyrit.executor"),
            "pyrit.executor.attack": types.ModuleType("pyrit.executor.attack"),
            "pyrit.prompt_target": types.ModuleType("pyrit.prompt_target"),
            "pyrit.converter": types.ModuleType("pyrit.converter"),
            "pyrit.score": types.ModuleType("pyrit.score"),
            "pyrit.memory": types.ModuleType("pyrit.memory"),
            "pyrit.setup": types.ModuleType("pyrit.setup"),
        }
        for name, mod in mods.items():
            self.saved[name] = sys.modules.get(name)
            sys.modules[name] = mod
        # 桩类
        class _Scorer:
            def __call__(self, *a, **k):
                return True
            def score(self, text=None, objective=None, **kwargs):
                # 桩评分器：文本非空即命中，验证评分器被真正调用（S2）
                return bool(text)
        mods["pyrit.score"].SubStringScorer = _Scorer
        mods["pyrit.score"].SelfAskRefusalScorer = _Scorer
        mods["pyrit.converter"].Base64Converter = _Scorer
        mods["pyrit.converter"].ROT13Converter = _Scorer
        mods["pyrit.converter"].LeetspeakConverter = _Scorer
        mods["pyrit.converter"].TranslationConverter = _Scorer
        class _Target:
            def __init__(self, **kwargs):
                self.kwargs = kwargs
        mods["pyrit.prompt_target"].OpenAIChatTarget = _Target
        class _Exec:
            def __init__(self, **kwargs):
                self.kwargs = kwargs
            def execute_attack_async(self, attack, objectives):
                return _Result()
        class _Result:
            last_response = "stubbed"
        mods["pyrit.executor.attack"].AttackExecutor = _Exec
        for cls in ("PromptSendingAttack", "CrescendoAttack", "PAIRAttack",
                    "TreeOfAttacksWithPruningAttack", "RedTeamingAttack"):
            setattr(mods["pyrit.executor.attack"], cls, _Target)
        self.mods = mods

    def tearDown(self):
        for name, val in self.saved.items():
            if val is None:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = val

    def test_real_backend_is_factory(self):
        self.assertIsInstance(RealPyRITBackend(), BackendFactory)

    def test_target_and_scorer(self):
        be = RealPyRITBackend(chat_endpoint="http://lab", api_key="k")
        self.assertEqual(be.make_target().kwargs["endpoint"], "http://lab")
        self.assertIsNotNone(be.make_scorer("deterministic"))

    def test_converter_names(self):
        be = RealPyRITBackend()
        for kind in ("base64", "rot13", "leetspeak", "translation"):
            self.assertIsNotNone(be.make_converter(kind))

    def test_execute_strategy(self):
        be = RealPyRITBackend(chat_endpoint="http://lab")
        r = be.execute("jailbreak-04", "越狱目标")
        self.assertEqual(r.verdict, "完全生效")
        self.assertTrue(r.deterministic_hit)

    def test_no_forbidden_names(self):
        import pathlib
        pkg = pathlib.Path(ROOT, "tools/attack_jailbreak")
        forbidden = ("pyrit.orchestrator", "Orchestrator", "AzureOpenAIChatTarget",
                     "execute_single_turn_attacks_async")
        for py in pkg.glob("*.py"):
            src = py.read_text(encoding="utf-8")
            for name in forbidden:
                self.assertNotIn(name, src, "%s 含禁用名 %s" % (py.name, name))


if __name__ == "__main__":
    unittest.main()
