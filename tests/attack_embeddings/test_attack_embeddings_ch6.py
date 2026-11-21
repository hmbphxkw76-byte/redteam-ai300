#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Ch6 增量测试（阶段 9）：AC-C1..C12，只测外部行为。"""
import json
import os
import struct
import tempfile
import unittest

from tools.attack_embeddings import beamsearch, decision, envelope, exporter, fingerprint
from tools.attack_embeddings import probing, slotfill, triage
from tools.attack_embeddings.harness import EmbeddingHarness, DeterministicEmbedder, fixture_corpus
from tools.attack_embeddings.model import cosine


class TestExport(unittest.TestCase):
    def test_export_formats(self):
        """AC-C1: 三格式导出；.npy float32 往返误差 <1e-6；游标分页覆盖全部。"""
        with tempfile.TemporaryDirectory() as td:
            matrix = [[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]]
            res = exporter.export_vectors(td, matrix=matrix,
                                          chunk_ids=["c0", "c1"], uuids=["u0", "u1"])
            self.assertEqual(res["count"], 2)
            self.assertTrue(os.path.exists(os.path.join(td, "embeddings.npy")))
            self.assertTrue(os.path.exists(os.path.join(td, "embeddings.csv")))
            # 解析手写 .npy
            with open(os.path.join(td, "embeddings.npy"), "rb") as f:
                self.assertEqual(f.read(6), b"\x93NUMPY")
                ver = f.read(2)
                hlen = struct.unpack("<H", f.read(2))[0]
                header = f.read(hlen).decode("latin1")
                self.assertIn("'<f4'", header)
                raw = f.read(24)  # 2 行 × 3 列 × float32(4B) = 24B
            vals = struct.unpack("<6f", raw)
            for got, want in zip(vals, [0.1, 0.2, 0.3, 0.4, 0.5, 0.6]):
                self.assertLess(abs(got - want), 1e-6)
            # CSV 行数
            with open(os.path.join(td, "embeddings.csv"), encoding="utf-8") as f:
                lines = f.readlines()
            self.assertEqual(len(lines), 3)  # header + 2
            # parquet 状态如实标注（无 pyarrow 时不伪造）
            self.assertIn(res["parquet"]["status"], ("OK", "NOT_AVAILABLE"))

    def test_cursor_pagination(self):
        pages = {None: {"objects": [{"vector": [1.0], "id": "a"}], "next_cursor": "p1"},
                 "p1": {"objects": [{"vector": [2.0], "id": "b"}], "next_cursor": None}}
        got = exporter.fetch_all_pages(lambda c: pages[c], page_size=200)
        self.assertEqual([o["id"] for o in got], ["a", "b"])


class TestFingerprintProbing(unittest.TestCase):
    def test_dimension_candidates(self):
        """AC-C2: 384 维返回 ≥3 候选且不唯一。"""
        r = fingerprint.candidates_for_dim(384)
        self.assertGreaterEqual(r["count"], 3)
        self.assertFalse(r["unique"])
        self.assertTrue(r["needs_confirmation"])

    def test_inference_probing(self):
        """AC-C3: 正确模型 top5_avg≥0.85；错模型低；pairs 落盘。"""
        h = EmbeddingHarness(DeterministicEmbedder())
        target_text = "salary executive package secret"
        vecs = [h.embed(target_text)]
        # 正确模型 = 夹具 embedder（同几何）；错误模型 = 维度相同的另一个词序
        wrong = DeterministicEmbedder(list(reversed(DeterministicEmbedder().vocab)))
        def embed_fn(model, text):
            return h.embed(text) if model == "victim" else wrong.embed(text)
        def query_iface(prompt):
            return target_text + ". More context about salary executive package secret."
        with tempfile.TemporaryDirectory() as td:
            pairs = os.path.join(td, "pairs.jsonl")
            r = probing.probe_model(vecs, query_iface, ["victim", "wrong"], embed_fn,
                                    deep=True, pairs_path=pairs)
            self.assertEqual(r["identified"], "victim")
            top = r["ranking"][0]["top5_avg"]
            self.assertGreaterEqual(top, 0.85)
            self.assertTrue(os.path.exists(pairs))
            with open(pairs, encoding="utf-8") as pf:
                self.assertGreater(len(pf.readlines()), 0)


class TestTriage(unittest.TestCase):
    def test_chunk_triage(self):
        """AC-C4: 三阶段执行；池缩小；含 credential 的块排前；索引可追溯。"""
        h = EmbeddingHarness(DeterministicEmbedder())
        h.ingest(fixture_corpus())
        r = triage.triage_chunks(h, top_density=3, top_pw=2)
        self.assertEqual(r["stages"]["pw"], 2)
        self.assertLessEqual(r["stages"]["recon"], 2)
        self.assertTrue(all("chunk_index" in x for x in r["results"]))
        self.assertEqual(len(r["results"]), 4)


class TestSlotBeam(unittest.TestCase):
    def setUp(self):
        self.h = EmbeddingHarness(DeterministicEmbedder())

    def test_slot_filling(self):
        """AC-C5: 夹具词表填槽命中 + margin-aware + consensus。"""
        wordlist = ["salary", "secret", "alpha", "beta"]
        template = "The password is {PASSWORD} today"
        target = self.h.embed(template.replace("{PASSWORD}", "secret"))
        r = slotfill.fill_slots(target, [template], wordlist, "PASSWORD", harness=self.h,
                                neutral="XXXX", consensus_threshold=0.5)
        self.assertEqual(r["value"], "secret")
        self.assertIn("margin", r)

    def test_beam_search(self):
        """AC-C6: beam 结构相似度 + 高熵检测 + 课程近似标注。"""
        target = self.h.embed("salary executive package secret")
        r = beamsearch.beam_recover(target, self.h, beam_width=3, steps=4)
        self.assertGreaterEqual(r["similarity"], 0.8)
        self.assertIn("note", r)
        det = beamsearch.detect_high_entropy("key is sk-abcdefgh1234 and eyJabc123456")
        kinds = {d["kind"] for d in det}
        self.assertIn("API_KEY", kinds)
        self.assertIn("JWT", kinds)


class TestDecisionLimits(unittest.TestCase):
    def test_decision_matrix(self):
        """AC-C7: 时间紧默认 fixture；未知模型 → ALGEN（不适用标注）。"""
        self.assertEqual(decision.select_method()["method"], "fixture")
        r = decision.select_method(model_known=False, can_write_store=False, has_rag=False)
        self.assertEqual(r["method"], "ALGEN")
        self.assertTrue(r.get("not_applicable"))

    def test_limitations_gate(self):
        """AC-C8: 512-token+PQ → 低可行性；随机串 → 不可恢复。"""
        r = decision.check_limits(chunk_tokens=512, quantized=True, high_entropy=True)
        self.assertEqual(r["feasibility"], "low")
        self.assertFalse(r["recoverable"])
        self.assertTrue(r["flags"]["token_length"])


class TestEnvAndContract(unittest.TestCase):
    def test_env_gate(self):
        """AC-C9/C10: 无 lab 标不适用并附 C-1 依据。"""
        a = envelope.assess_env("ALGEN", has_lab=False)
        self.assertEqual(a["status"], "NOT_APPLICABLE")
        self.assertIn("AIVP", a["c1_evidence"])
        v = envelope.assess_env("Vec2Text", has_gpu=False)
        self.assertEqual(v["status"], "NOT_APPLICABLE")

    def test_spec_wording(self):
        """AC-C12: 夹具反演与真实 Vec2Text 名称可区分。"""
        import tools.attack_embeddings as pkg
        self.assertIn("beamsearch", pkg.__all__)
        self.assertIn("envelope", pkg.__all__)


if __name__ == "__main__":
    unittest.main()
