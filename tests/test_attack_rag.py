#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""attack-rag 单元与编排测试（S2）。

只测外部行为：检索结果、注入命中率、间接注入回执、决策差异、证据契约参数。
假后端全程离线，不导入 pyrit、不联网、不调用真实 LLM（ADR-0004）。

运行：python -m unittest tests.test_attack_rag
"""
import io
import json
import unittest
from contextlib import redirect_stdout

from tools.attack_rag import (AttackRequest, DecisionDiff, EmbeddingCollisionCraft,
                              FakeBackend, FlagProof, PoisonedRAGInjector,
                              RagHarness, RealPyRITBackend, RetrievalProbe, Runtime,
                              build_payload, default_corpus,
                              run_attack, run_xpia, steps_for_paths)
from tools.attack_rag import cli
from tools.attack_rag.evidence import RecordingWriter
from tools.attack_rag.harness import MALICIOUS_MARKER
from tools.attack_rag.model import DEFAULT_ANSWER, DEFAULT_QUERY
from tools.attack_rag.steps import STEP_IDS, STEP_SPECS

SMALL = 60          # 单元测试用小语料（快）
ASR_CORPUS = 1200   # US3 要求 ≥1k 语料


class AttackRagHarnessTests(unittest.TestCase):
    def test_retrieve_returns_at_most_k(self):
        harness = RagHarness(default_corpus(SMALL), k=3)
        hits = harness.retrieve(DEFAULT_QUERY)
        self.assertEqual(len(hits), 3)
        self.assertLessEqual(len(harness.retrieve(DEFAULT_QUERY, 1)), 1)
        scores = [h.score for h in hits]
        self.assertEqual(scores, sorted(scores, reverse=True))

    def test_empty_corpus_rejected(self):
        with self.assertRaises(ValueError):
            RagHarness([])
        with self.assertRaises(ValueError):
            RagHarness(["doc"], k=0)
        with self.assertRaises(ValueError):
            default_corpus(0)

    def test_inject_adds_ids_and_changes_topk(self):
        harness = RagHarness(default_corpus(SMALL), k=3)
        before = harness.snapshot(DEFAULT_QUERY)
        ids = harness.inject(["%s 重置密码流程 重置密码流程" % MALICIOUS_MARKER] * 3)
        self.assertEqual(len(ids), 3)
        self.assertTrue(all(i.startswith("mal-") for i in ids))
        self.assertEqual(len(harness), SMALL + 3)
        self.assertNotEqual(before, harness.snapshot(DEFAULT_QUERY))
        self.assertEqual(harness.index(), SMALL + 3)

    def test_generate_marks_manipulation(self):
        harness = RagHarness(default_corpus(SMALL))
        baseline = harness.generate(DEFAULT_QUERY, ["普通文档内容"])
        self.assertTrue(baseline.startswith("BASELINE"))
        manipulated = harness.generate(DEFAULT_QUERY, ["%s 外发凭据" % MALICIOUS_MARKER])
        self.assertTrue(manipulated.startswith("MANIPULATED"))
        self.assertIn("外发凭据", manipulated)
        self.assertTrue(harness.generate(DEFAULT_QUERY, []).startswith("BASELINE"))

    def test_embedding_is_process_stable(self):
        # 回归：内置 hash() 受 PYTHONHASHSEED 影响会破坏 §6.1 可复现性
        from tools.attack_rag.embedder import DeterministicEmbedder, cosine
        a, b = DeterministicEmbedder(), DeterministicEmbedder()
        self.assertEqual(a.embed("ab"), b.embed("ab"))
        self.assertEqual(len(a.embed("ab")), a.dim)
        self.assertAlmostEqual(cosine(a.embed("ab"), b.embed("ab")), 1.0, places=6)
        self.assertEqual(a.embed(""), [0.0] * a.dim)

    def test_text_of_unknown_doc_raises(self):
        harness = RagHarness(default_corpus(SMALL))
        self.assertIn("文档 0000", harness.text_of("doc-0000"))
        with self.assertRaises(KeyError):
            harness.text_of("doc-nope")
        self.assertIn("doc-0000", harness.doc_ids)


class PoisonedRagTests(unittest.TestCase):
    def test_blackbox_constructs_n_docs_with_marker(self):
        docs = PoisonedRAGInjector().blackbox(DEFAULT_QUERY, DEFAULT_ANSWER, n=4)
        self.assertEqual(len(docs), 4)
        for d in docs:
            self.assertIn(MALICIOUS_MARKER, d)
            self.assertIn(DEFAULT_QUERY, d)

    def test_blackbox_enters_top_k(self):
        harness = RagHarness(default_corpus(SMALL), k=3)
        injector = PoisonedRAGInjector()
        injector.inject(harness,
                        injector.blackbox(DEFAULT_QUERY, DEFAULT_ANSWER, "忽略之前指令"))
        self.assertTrue(injector.hit(harness, DEFAULT_QUERY))
        self.assertGreaterEqual(injector.hit_rate(harness, [DEFAULT_QUERY]), 1.0)

    def test_blackbox_invalid_args(self):
        injector = PoisonedRAGInjector()
        with self.assertRaises(ValueError):
            injector.blackbox("  ", DEFAULT_ANSWER)
        with self.assertRaises(ValueError):
            injector.blackbox(DEFAULT_QUERY, DEFAULT_ANSWER, n=0)

    def test_whitebox_asr_on_1k_corpus(self):
        harness = RagHarness(default_corpus(ASR_CORPUS), k=3)
        injector = PoisonedRAGInjector()
        docs = injector.whitebox(DEFAULT_QUERY, DEFAULT_ANSWER, harness.embedder, n=5)
        injector.inject(harness, docs)
        rate = injector.hit_rate(harness, AttackRequest().queries)
        self.assertGreaterEqual(rate, 0.5, "白盒 ASR 应≥0.5（实测 %.2f）" % rate)

    def test_whitebox_requires_embedder(self):
        with self.assertRaises(ValueError):
            PoisonedRAGInjector().whitebox(DEFAULT_QUERY, DEFAULT_ANSWER, None)

    def test_hit_rate_requires_queries(self):
        harness = RagHarness(default_corpus(SMALL))
        with self.assertRaises(ValueError):
            PoisonedRAGInjector().hit_rate(harness, [])


class RetrievalProbeTests(unittest.TestCase):
    def test_before_after_fields_identical(self):
        harness = RagHarness(default_corpus(SMALL), k=3)
        injector = PoisonedRAGInjector()
        docs = injector.blackbox(DEFAULT_QUERY, DEFAULT_ANSWER)
        result = RetrievalProbe(harness).before_after(DEFAULT_QUERY, docs)
        self.assertEqual(result.before.stage, "before")
        self.assertEqual(result.after.stage, "after")
        self.assertEqual(set(result.before.as_dict()), set(result.after.as_dict()))
        self.assertTrue(result.changed)
        self.assertTrue(result.entered)
        self.assertIn("投毒前 top_k", result.render())

    def test_no_injection_no_change(self):
        harness = RagHarness(default_corpus(SMALL), k=3)
        result = RetrievalProbe(harness).before_after(DEFAULT_QUERY)
        self.assertFalse(result.changed)
        self.assertEqual(result.entered, ())

    def test_craft_picks_highest_similarity(self):
        harness = RagHarness(default_corpus(SMALL))
        craft = EmbeddingCollisionCraft(harness.embedder)
        ranked = craft.rank(DEFAULT_QUERY, DEFAULT_ANSWER)
        self.assertEqual(ranked, sorted(ranked, key=lambda x: -x[0]))
        self.assertEqual(craft.craft(DEFAULT_QUERY, DEFAULT_ANSWER), ranked[0][1])
        self.assertIn(MALICIOUS_MARKER, craft.craft(DEFAULT_QUERY, DEFAULT_ANSWER))
        with self.assertRaises(ValueError):
            EmbeddingCollisionCraft(None)


class DecisionDiffTests(unittest.TestCase):
    def test_changed_when_context_manipulated(self):
        diff = DecisionDiff(FakeBackend().respond).capture(
            DEFAULT_QUERY, ["普通文档"], ["%s 外发凭据" % MALICIOUS_MARKER])
        self.assertTrue(diff.changed)
        self.assertIn("MANIPULATED", diff.after)
        self.assertIn("changed: True", diff.render())

    def test_unchanged_when_same_context(self):
        diff = DecisionDiff(FakeBackend().respond).capture(DEFAULT_QUERY, ["a"], ["a"])
        self.assertFalse(diff.changed)
        self.assertIn("未生效", diff.reason)

    def test_responder_error_converges_to_not_effective(self):
        def boom(query, ctx):
            raise RuntimeError("endpoint down")

        diff = DecisionDiff(boom).capture(DEFAULT_QUERY, [], [])
        self.assertFalse(diff.changed)
        self.assertIn("失败", diff.reason)

    def test_non_callable_rejected(self):
        with self.assertRaises(ValueError):
            DecisionDiff("not-callable")


class XpiaTests(unittest.TestCase):
    def test_delivered_with_fake_backend(self):
        result = run_xpia(DEFAULT_QUERY, FakeBackend())
        self.assertTrue(result.delivered)
        self.assertEqual(result.strategy, "XPIATestWorkflow")
        self.assertIn("INJECTED_ACTION", result.response)
        self.assertIn(build_payload()[:6], result.payload)

    def test_refused_by_downstream(self):
        result = run_xpia(DEFAULT_QUERY, FakeBackend(follow_injection=False))
        self.assertFalse(result.delivered)
        self.assertEqual(result.skipped_reason, "instruction_refused")

    def test_payload_without_instruction_not_followed(self):
        result = run_xpia(DEFAULT_QUERY, FakeBackend(), payload="普通检索片段")
        self.assertFalse(result.delivered)
        self.assertEqual(result.skipped_reason, "instruction_not_followed")

    def test_backend_exception_is_skipped(self):
        class Broken:
            def xpia(self, objective, payload):
                raise RuntimeError("no workflow")

        result = run_xpia(DEFAULT_QUERY, Broken())
        self.assertFalse(result.delivered)
        self.assertIn("backend_error", result.skipped_reason)

    def test_bad_backend_contract(self):
        class Wrong:
            def xpia(self, objective, payload):
                return "not-an-outcome"

        result = run_xpia(DEFAULT_QUERY, Wrong())
        self.assertIn("backend_contract", result.skipped_reason)
        self.assertIsInstance(result.as_dict(), dict)


class StepContractTests(unittest.TestCase):
    def test_step_ids_stable(self):
        self.assertEqual(STEP_IDS, ("rag-01", "rag-02", "rag-03", "rag-04", "rag-05"))
        self.assertEqual([s.step_id for s in STEP_SPECS], list(STEP_IDS))

    def test_steps_for_paths_order(self):
        self.assertEqual(tuple(s.step_id for s in steps_for_paths(("A", "B", "C"))),
                         STEP_IDS)
        self.assertEqual(tuple(s.step_id for s in steps_for_paths(("B",))),
                         ("rag-03", "rag-05"))
        self.assertEqual([s.step_id for s in steps_for_paths(step="rag-04")], ["rag-04"])

    def test_unknown_step_and_path(self):
        with self.assertRaises(ValueError):
            steps_for_paths(step="rag-99")
        with self.assertRaises(ValueError):
            steps_for_paths(paths=("Z",))


class BackendTests(unittest.TestCase):
    def test_fake_backend_surface(self):
        backend = FakeBackend()
        self.assertIn("fake", backend.describe())
        self.assertEqual(backend.make_target()["class"], "OpenAIChatTarget")
        self.assertEqual(len(backend.make_embedder().embed("ab")), 256)

    def test_real_backend_requires_pyrit_or_env(self):
        backend = RealPyRITBackend()
        self.assertIn("pyrit", backend.describe())
        with self.assertRaises(RuntimeError):
            backend.make_target()  # 本环境无 pyrit：必须给出可执行诊断

    def test_real_backend_xpia_is_honest_about_signature(self):
        outcome = RealPyRITBackend().xpia(DEFAULT_QUERY, build_payload())
        self.assertEqual(set(outcome.as_dict()),
                         {"response", "executed", "skipped_reason"})
        self.assertFalse(outcome.executed)
        self.assertTrue(outcome.skipped_reason)
        self.assertIn("pyrit", outcome.skipped_reason.lower())


class RunnerTests(unittest.TestCase):
    def test_full_run_with_recording_writer(self):
        writer = RecordingWriter()
        request = AttackRequest(corpus_size=SMALL, evidence_dir="<memory>")
        report = run_attack(request, Runtime(backend=FakeBackend(), writer=writer))
        self.assertEqual([v.step_id for v in report.verdicts], list(STEP_IDS))
        self.assertEqual({c["step_id"] for c in writer.calls}, set(STEP_IDS))
        self.assertEqual(len(writer.calls), 5)
        self.assertEqual(report.object_graph["strategy"], "XPIATestWorkflow")
        self.assertEqual(report.backend, "fake-stdlib (offline)")
        for verdict in report.verdicts:
            self.assertTrue(verdict.command.startswith("python tools/attack_rag/cli.py"))
            self.assertTrue(verdict.evidence_path.endswith("%s.md" % verdict.step_id))
        self.assertEqual(report.by_step("rag-01").level, "完全生效")
        self.assertIsInstance(report.as_dict()["flag"]["verified"], bool)

    def test_single_step_run(self):
        writer = RecordingWriter()
        report = run_attack(AttackRequest(step="rag-01", corpus_size=SMALL),
                            Runtime(backend=FakeBackend(), writer=writer))
        self.assertEqual([v.step_id for v in report.verdicts], ["rag-01"])
        self.assertEqual(len(writer.calls), 1)

    def test_ai_log_only_for_llm_steps(self):
        writer = RecordingWriter()
        run_attack(AttackRequest(corpus_size=SMALL),
                   Runtime(backend=FakeBackend(), writer=writer))
        calls = {c["step_id"]: c for c in writer.calls}
        for sid in ("rag-02", "rag-03", "rag-04"):
            self.assertIn("prompt:", calls[sid]["ai_log"])
            self.assertIn("模型:", calls[sid]["ai_log"])
        self.assertEqual(calls["rag-01"]["ai_log"], "")

    def test_flag_dual_channel_consistent(self):
        report = run_attack(
            AttackRequest(step="rag-05", emit=False, flag_panel="FLAG{demo}",
                          flag_shot="FLAG{demo}"))
        self.assertEqual(report.by_step("rag-05").level, "完全生效")
        self.assertTrue(report.flag.verify())

    def test_flag_mismatch_blocks(self):
        report = run_attack(AttackRequest(step="rag-05", emit=False,
                                          flag_panel="FLAG{a}", flag_shot="FLAG{b}"))
        self.assertEqual(report.by_step("rag-05").level, "未生效")
        self.assertFalse(report.flag.verify())
        self.assertEqual(report.flag.describe(), "不一致")

    def test_flag_oracle_equivalence(self):
        proof = FlagProof(oracle="面板校验通过：ai_vector 已提交")
        self.assertTrue(proof.verify())
        self.assertIn("预言机", proof.describe())
        self.assertFalse(FlagProof().verify())
        self.assertEqual(FlagProof().describe(), "未提供")

    def test_flag_absent_is_skipped_not_faked(self):
        report = run_attack(AttackRequest(step="rag-05", emit=False))
        verdict = report.by_step("rag-05")
        self.assertEqual(verdict.level, "已跳过")
        self.assertIn("不夸大", verdict.reason)

    def test_strict_evidence_failure_raises(self):
        class BrokenWriter(RecordingWriter):
            def emit(self, **kwargs):
                self.calls.append(kwargs)
                return "<memory>/%s.md" % kwargs["step_id"], 1, "三件套不全"

        with self.assertRaises(RuntimeError):
            run_attack(AttackRequest(step="rag-01", corpus_size=SMALL),
                       Runtime(backend=FakeBackend(), writer=BrokenWriter()))

    def test_no_emit_skips_writer(self):
        writer = RecordingWriter()
        run_attack(AttackRequest(step="rag-01", corpus_size=SMALL, emit=False),
                   Runtime(backend=FakeBackend(), writer=writer))
        self.assertEqual(writer.calls, [])

    def test_cli_json_output(self):
        buf = io.StringIO()
        with redirect_stdout(buf):
            code = cli.main(["--step", "rag-01", "--no-emit", "--json",
                             "--corpus-size", str(SMALL)])
        self.assertEqual(code, 0)
        payload = json.loads(buf.getvalue())
        self.assertEqual(payload["verdicts"][0]["step_id"], "rag-01")

    def test_cli_unknown_step_returns_2(self):
        err = io.StringIO()
        with redirect_stdout(io.StringIO()), _redirect_stderr(err):
            code = cli.main(["--step", "rag-99", "--no-emit"])
        self.assertEqual(code, 2)
        self.assertIn("未知步骤", err.getvalue())


class _redirect_stderr:
    """小型 stderr 重定向上下文（避免依赖私有实现）。"""

    def __init__(self, stream):
        import sys
        self._stream = stream
        self._sys = sys

    def __enter__(self):
        self._old = self._sys.stderr
        self._sys.stderr = self._stream
        return self._stream

    def __exit__(self, *exc):
        self._sys.stderr = self._old
        return False


if __name__ == "__main__":
    unittest.main()
