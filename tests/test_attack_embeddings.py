#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""attack-embeddings 行为测试（阶段 9）。

只测外部行为（还原率 / AUC / 相似度偏移 / 命中 / 降级），不断言内部实现细节。
覆盖规格 v2 AC-1..AC-11。运行：python -m unittest discover -s tests -q
"""
import unittest

from tools.attack_embeddings import (DeterministicEmbedder, EmbeddingHarness,
                                     FakeRagTarget, InMemoryVectorStore,
                                     adversarial_shift, fixture_corpus,
                                     invert, membership_auc,
                                     membership_inference, rag_impact,
                                     run_attack, vector_lookup)
from tools.attack_embeddings.model import AttackRequest
from tools.attack_embeddings.runner import Runtime


def _harness():
    h = EmbeddingHarness(DeterministicEmbedder())
    h.ingest(fixture_corpus())
    return h


class TestAttackEmbeddingsBehavior(unittest.TestCase):
    # AC-1 定位 embedding 面
    def test_surface_enumeration(self):
        rep = run_attack(AttackRequest())
        self.assertEqual(rep.levels()["emb-01"], "完全生效")

    # AC-2 探测维度
    def test_probe_dimensions(self):
        h = _harness()
        rep = run_attack(AttackRequest(), Runtime(h, FakeRagTarget(), Runtime.default().evidence))
        expected = h.embedder.dim
        self.assertEqual(int(rep.steps[1].metrics["dimensions"]), expected)

    # AC-3 反演精确还原
    def test_invert_exact_match(self):
        h = _harness()
        text = fixture_corpus()["doc-1"]
        out = invert(h.embed(text), h)
        self.assertEqual(out["text"], text)
        self.assertGreaterEqual(out["confidence"], 0.99)

    # AC-4 成员推断 AUC
    def test_membership_auc(self):
        h = _harness()
        members = list(fixture_corpus().values())
        nonmembers = ["zeta eta theta", "alpha gamma delta"]
        auc = membership_auc(members, nonmembers, h)
        self.assertGreaterEqual(auc, 0.65)

    def test_membership_single(self):
        h = _harness()
        m = membership_inference(fixture_corpus()["doc-2"], h)
        self.assertTrue(m["member"])
        self.assertGreaterEqual(m["score"], 0.98)

    # AC-5 对抗扰动
    def test_adversarial_shift(self):
        h = _harness()
        adv = adversarial_shift("alpha beta gamma", "salary executive package", h)
        self.assertGreater(adv["delta"], 0.0)
        self.assertGreaterEqual(adv["after"], adv["before"])

    # AC-6 向量库反查
    def test_vector_lookup(self):
        h = _harness()
        hits = vector_lookup("salary executive", h, k=3)
        self.assertGreaterEqual(len(hits), 1)
        self.assertIn("text", hits[0])
        self.assertTrue(any("salary" in str(x["text"]) for x in hits))

    def test_vector_lookup_empty_store(self):
        h = EmbeddingHarness(DeterministicEmbedder(), InMemoryVectorStore())
        self.assertEqual(vector_lookup("salary", h, k=3), [])

    # AC-7 下游 RAG 影响
    def test_rag_impact(self):
        h = _harness()
        out = rag_impact("salary executive", h, "salary executive poison", FakeRagTarget(), k=3)
        self.assertTrue(out["changed"])
        self.assertTrue(out["ai_log_path"])
        self.assertIn("poison-1", out["manipulated_ids"])

    # AC-8 flag 双通道
    def test_flag_dual_channel(self):
        rep = run_attack(AttackRequest(flag="FLAG{abc}"))
        self.assertEqual(rep.levels()["emb-08"], "完全生效")
        rep2 = run_attack(AttackRequest())
        self.assertEqual(rep2.levels()["emb-08"], "部分生效")

    # AC-9 可复现
    def test_reproducible(self):
        r1 = run_attack(AttackRequest())
        r2 = run_attack(AttackRequest())
        self.assertEqual(r1.levels(), r2.levels())

    # AC-10 证据接线：每步一次 emit
    def test_evidence_wiring(self):
        rt = Runtime.default()
        run_attack(AttackRequest(), rt)
        got = [c.get("step_id") for c in rt.evidence.calls]
        self.assertEqual(got, ["emb-0%d" % i for i in range(1, 9)])

    # AC-11 降级路径
    def test_fallback_paths(self):
        rep = run_attack(AttackRequest(has_surface=False))
        self.assertTrue(rep.degraded)
        self.assertTrue(all(s.level == "已跳过" for s in rep.steps))

    # CLI 入口（覆盖 cli.py）
    def test_cli_main(self):
        import contextlib
        import io
        from tools.attack_embeddings import cli
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = cli.main(["--sample", "salary executive package secret",
                           "--concept", "salary executive", "--flag", "FLAG{t}"])
        self.assertEqual(rc, 0)
        out = buf.getvalue()
        self.assertIn("degraded=False", out)
        self.assertIn("emb-08", out)

    def test_cli_degraded(self):
        import contextlib
        import io
        from tools.attack_embeddings import cli
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = cli.main(["--degraded"])
        self.assertEqual(rc, 0)
        self.assertIn("degraded=True", buf.getvalue())

    # 错误行为
    def test_errors(self):
        h = _harness()
        with self.assertRaises(ValueError):
            invert([], h)
        with self.assertRaises(ValueError):
            membership_inference("   ", h)
        with self.assertRaises(ValueError):
            vector_lookup("x", h, k=0)
        with self.assertRaises(ValueError):
            adversarial_shift("", "salary", h)


if __name__ == "__main__":
    unittest.main()
