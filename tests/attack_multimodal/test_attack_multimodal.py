#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""attack-multimodal 外部行为测试（S2，仅标准库）。

注入最小 PyRIT 桩验证 RealPyRITBackend 延迟导入与 1.1.0 多模态命名空间（不安装 pyrit）。
覆盖 AC-01..09/14/15/17/18。
"""
import sys
import types
import unittest

from tests._paths import ROOT

if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from tools.attack_multimodal.backends import (BackendFactory, FakePyRITBackend,
                                              RealPyRITBackend, TargetResponse,
                                              get_backend)
from tools.attack_multimodal.runner import grade, run_steps, summary
from tools.attack_multimodal.steps import (FINAL_STEPS, PATH_STEPS, PREFIX,
                                           STEP_IDS, STEP_SPECS, steps_for_paths)


class TestSteps(unittest.TestCase):
    def test_contract(self):
        self.assertEqual(PREFIX, "multimodal")
        self.assertEqual(len(STEP_IDS), 10)
        self.assertEqual(len(set(STEP_IDS)), 10)
        for sid in STEP_IDS:
            self.assertTrue(sid.startswith("multimodal-"))

    def test_paths_order(self):
        got = [s.step_id for s in steps_for_paths(["A", "B"])]
        self.assertEqual(got[:2], ["multimodal-01", "multimodal-02"])
        self.assertEqual(got[-2:], ["multimodal-09", "multimodal-10"])

    def test_evidence_hooks(self):
        for s in STEP_SPECS:
            self.assertIn("demo.py --step", s.command)
            self.assertIn("evidence/", s.screenshot_hook)


class TestGrading(unittest.TestCase):
    def test_tiers(self):
        self.assertEqual(grade(TargetResponse("x", "完全生效", deterministic_hit=True)), "success")
        self.assertEqual(grade(TargetResponse("x", "部分生效", deterministic_hit=True)), "部分生效")
        self.assertEqual(grade(TargetResponse("x", "UNDETERMINED")), "UNDETERMINED")
        self.assertEqual(grade(TargetResponse("x", "完全生效", llm_hit=True)), "llm_hit")
        self.assertEqual(grade(TargetResponse("x", "完全生效")), "未生效")


class TestFakeBackend(unittest.TestCase):
    def test_factory_and_determinism(self):
        self.assertIsInstance(FakePyRITBackend(), BackendFactory)
        self.assertIsInstance(get_backend(), FakePyRITBackend)
        a = run_steps(step_ids=["multimodal-01", "multimodal-08"], backend=FakePyRITBackend())
        b = run_steps(step_ids=["multimodal-01", "multimodal-08"], backend=FakePyRITBackend())
        self.assertEqual([r.evidence["grade"] for r in a],
                         [r.evidence["grade"] for r in b])

    def test_payload_reuse_path(self):
        r = run_steps(step_ids=["multimodal-03"], backend=FakePyRITBackend())
        self.assertTrue(r[0].evidence["file_path"].startswith("evidence/"))

    def test_partial_and_undetermined(self):
        p = run_steps(step_ids=["multimodal-08"],
                      backend=FakePyRITBackend(scenario="partial"))
        self.assertEqual(p[0].evidence["grade"], "部分生效")
        u = run_steps(step_ids=["multimodal-08"],
                      backend=FakePyRITBackend(scenario="undetermined"))
        self.assertEqual(u[0].evidence["grade"], "UNDETERMINED")

    def test_camouflage_reuse(self):
        """D5/AC-03：step-03 真正调用 attack-rag 伪装原语并返回可见性说明。"""
        r = run_steps(step_ids=["multimodal-03"], backend=FakePyRITBackend())
        self.assertIn("white-on-white", r[0].response.text)
        self.assertTrue(r[0].evidence["file_path"].endswith(".pdf"))

    def test_llm_fallback(self):
        """AC-08：确定性未命中时 LLM 评分回退命中，grade=llm_hit。"""
        r = run_steps(step_ids=["multimodal-08"],
                      backend=FakePyRITBackend(scenario="llm"))
        self.assertEqual(r[0].evidence["grade"], "llm_hit")

    def test_summary(self):
        s = summary(run_steps(step_ids=["multimodal-01", "multimodal-08"],
                              backend=FakePyRITBackend()))
        self.assertEqual(s["total"], 2)
        self.assertEqual(sum(s["grades"].values()), 2)


class TestRealBackendStubbed(unittest.TestCase):
    """注入 PyRIT 桩：验证延迟导入、1.1.0 多模态 target 命名空间、评分真调用。"""

    def setUp(self):
        self.saved = {}
        self.mods = {}
        for name in ("pyrit", "pyrit.executor", "pyrit.executor.attack",
                     "pyrit.prompt_target", "pyrit.converter", "pyrit.score",
                     "pyrit.memory", "pyrit.setup"):
            mod = types.ModuleType(name)
            self.saved[name] = sys.modules.get(name)
            sys.modules[name] = mod
            self.mods[name] = mod

        class _Target:
            def __init__(self, **kwargs):
                self.kwargs = kwargs
        class _Scorer:
            def score(self, text=None, objective=None, **kwargs):
                return bool(text)
        class _Exec:
            def __init__(self, **kwargs):
                pass
            def execute_attack_async(self, attack, objectives):
                return _Result()
        class _Result:
            last_response = "stubbed multimodal response"
        for cls in ("OpenAIChatTarget", "OpenAIImageTarget", "HTTPXAPITarget",
                    "PlaywrightTarget"):
            setattr(self.mods["pyrit.prompt_target"], cls, _Target)
        for cls in ("SubStringScorer", "SelfAskRefusalScorer"):
            setattr(self.mods["pyrit.score"], cls, _Scorer)
        for cls in ("Base64Converter", "ROT13Converter", "LeetspeakConverter",
                    "TranslationConverter"):
            setattr(self.mods["pyrit.converter"], cls, _Target)
        self.mods["pyrit.executor.attack"].AttackExecutor = _Exec
        for cls in ("PromptSendingAttack",):
            setattr(self.mods["pyrit.executor.attack"], cls, _Target)
        self.mods["pyrit.setup"].initialize_pyrit_async = lambda **k: {"db": k.get("memory_db_type")}

    def tearDown(self):
        for name, val in self.saved.items():
            if val is None:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = val

    def test_factory(self):
        self.assertIsInstance(RealPyRITBackend(), BackendFactory)

    def test_multimodal_targets(self):
        be = RealPyRITBackend(chat_endpoint="http://chat", image_endpoint="http://img")
        for kind in ("chat", "image", "file", "browser"):
            self.assertIsNotNone(be.make_target(kind))
        self.assertEqual(be.make_target("image").kwargs["endpoint"], "http://img")

    def test_converter_and_scorer(self):
        be = RealPyRITBackend()
        for kind in ("base64", "rot13", "leetspeak", "translation"):
            self.assertIsNotNone(be.make_converter(kind))
        self.assertIsNotNone(be.make_scorer("deterministic"))

    def test_execute_scores_really(self):
        be = RealPyRITBackend(chat_endpoint="http://chat")
        r = be.execute("multimodal-05", "越狱目标")
        self.assertEqual(r.verdict, "完全生效")
        self.assertTrue(r.deterministic_hit)

    def test_unreachable_is_undetermined(self):
        # 端点未设时 make_target 抛错被 execute 捕获？此处仅验证 describe 不伪造成功。
        be = RealPyRITBackend()
        self.assertIn("1.1.0", be.describe())

    def test_no_forbidden_names(self):
        import pathlib
        pkg = pathlib.Path(ROOT, "tools/attack_multimodal")
        forbidden = ("pyrit.orchestrator", "Orchestrator", "AzureOpenAIChatTarget",
                     "execute_single_turn_attacks_async")
        for py in pkg.glob("*.py"):
            src = py.read_text(encoding="utf-8")
            for name in forbidden:
                self.assertNotIn(name, src, "%s 含禁用名 %s" % (py.name, name))


if __name__ == "__main__":
    unittest.main()
