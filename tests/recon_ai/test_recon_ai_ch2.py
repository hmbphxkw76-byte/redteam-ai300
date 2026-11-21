#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Ch2 旁路分析层单测：六类行为指纹、RAG 元数据、诱饵识别、检测规避与校验。

零网络：全部使用内存观测数据，验证「不推断未观测事实、不落盘明文凭据、
单信号不定家族」三条不可豁免边界。
"""
import json
import os
import sys
import tempfile
import unittest

from tests._paths import ROOT  # noqa: E402
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from tools.recon_ai import ch2, cli  # noqa: E402


class TaxonomyAndHeadersTests(unittest.TestCase):
    def test_taxonomy_maps_four_layers_to_seven_steps(self):
        steps = [s for _layer, group, _p in ch2.TAXONOMY for s in group]
        self.assertEqual(steps, ["recon-%02d" % i for i in range(1, 8)])

    def test_ai_headers_only_observed(self):
        signals = ch2.parse_ai_headers({"X-AI-Backend": "OpenAI-GPT5.2",
                                        "X-RAG-Provider": "ChromaDB"})
        self.assertEqual([s.value for s in signals], ["OpenAI-GPT5.2", "ChromaDB"])
        self.assertEqual(ch2.parse_ai_headers({"Server": "nginx"})[0].kind,
                         "header:Server")
        self.assertEqual(ch2.parse_ai_headers({}), [])

    def test_health_requires_status_or_model(self):
        self.assertEqual(ch2.parse_health_config('{"foo":1}'), [])
        self.assertEqual(ch2.parse_health_config("not json"), [])
        got = ch2.parse_health_config(
            '{"status":"healthy","model":"gpt-5.2-turbo","mcp_enabled":true}')
        self.assertEqual({s.kind for s in got},
                         {"health:status", "health:model", "health:mcp_enabled"})


class EndpointStatusTests(unittest.TestCase):
    def test_401_vs_404_semantics(self):
        self.assertEqual(ch2.classify_endpoint_status(401), "AUTH_REQUIRED")
        self.assertEqual(ch2.classify_endpoint_status(403), "AUTH_REQUIRED")
        self.assertEqual(ch2.classify_endpoint_status(404), "ABSENT")
        self.assertEqual(ch2.classify_endpoint_status(200), "PRESENT")
        self.assertEqual(ch2.classify_endpoint_status(None), "UNDETERMINED")


class BehaviorFingerprintTests(unittest.TestCase):
    def test_all_six_techniques(self):
        obs = [
            {"technique": "identity", "response": "I am Qwen from Alibaba Cloud"},
            {"technique": "contradiction", "response": "I must correct you, I am Llama by Meta AI"},
            {"technique": "cutoff", "response": "My knowledge cutoff is December 2023"},
            {"technique": "style", "response": 'def f():\n    """doc"""\n    # example usage'},
            {"technique": "capability", "response": "248,171", "expected": "248171"},
            {"technique": "context", "marker": "ZEBRA-42", "recalled": False},
        ]
        finding = ch2.fingerprint_behavior(obs)
        kinds = {s.kind for s in finding.signals}
        self.assertEqual(len(kinds), 6)
        self.assertIn("behavior:context", kinds)
        self.assertIn("behavior:capability", kinds)
        self.assertEqual(ch2.validate_analysis({"findings": [finding.to_dict()]}), [])

    def test_single_signal_does_not_conclude_family(self):
        finding = ch2.fingerprint_behavior(
            [{"technique": "identity", "response": "I am Qwen"}])
        self.assertNotIn("多信号一致指向", finding.note)
        result = {"findings": [finding.to_dict()]}
        self.assertEqual(ch2.validate_analysis(result), [])

    def test_unknown_technique_ignored(self):
        finding = ch2.fingerprint_behavior(
            [{"technique": "jailbreak", "response": "I am Qwen"}])
        self.assertEqual(finding.verdict, "不可判定")


class RagMetadataTests(unittest.TestCase):
    BODY = json.dumps({"sources": [{
        "title": "PTO_Leave_Policy_2024.pdf", "chunk_id": "chunk_087",
        "text": "Vacation accrual", "vector_score": 0.2,
        "bm25_score": 2.1, "combined_score": 0.51,
    }]})

    def test_disclosure_levels(self):
        self.assertEqual(ch2.classify_disclosure({"title": "a"}), "minimal")
        self.assertEqual(ch2.classify_disclosure({"title": "a", "text": "b"}), "moderate")
        self.assertEqual(ch2.classify_disclosure(
            {"title": "a", "text": "b", "chunk_id": "c", "vector_score": 0.2}), "detailed")
        self.assertEqual(ch2.classify_disclosure({}), "none")

    def test_source_parsing_truncates_text(self):
        body = json.dumps({"sources": [{"title": "x", "text": "A" * 500}]})
        group = ch2.parse_rag_sources(body)[0]
        text = next(s.value for s in group if s.kind == "source:text")
        self.assertLessEqual(len(text), 201)

    def test_kb_mapping_aggregates(self):
        groups = ch2.parse_rag_sources(self.BODY)
        finding = ch2.map_knowledge_base(groups + groups)
        self.assertIn("kb:documents", {s.kind for s in finding.signals})
        self.assertIn("kb:chunk_range", {s.kind for s in finding.signals})

    def test_empty_sources_yields_no_mapping(self):
        self.assertEqual(ch2.map_knowledge_base(
            ch2.parse_rag_sources('{"sources":[]}')).verdict, "不可判定")


class CanaryTests(unittest.TestCase):
    def test_canary_indicators(self):
        finding = ch2.detect_canary(
            "AKIAIOSFODNN7HONEYPOT; pw NovaTech2024!; http://db01.internal; "
            "Access Key ID / Secret Access Key / Account ID / Console URL")
        kinds = {s.kind for s in finding.signals}
        self.assertIn("canary:marker", kinds)
        self.assertIn("canary:password", kinds)
        self.assertIn("canary:url", kinds)
        self.assertIn("canary:completeness", kinds)

    def test_no_plaintext_secret_in_signals(self):
        finding = ch2.detect_canary("password NovaTech2024!")
        signal = next(s for s in finding.signals if s.kind == "canary:password")
        self.assertTrue(signal.value.startswith("Bearer-"))
        self.assertNotIn("NovaTech2024!", signal.value)

    def test_clean_text_not_flagged(self):
        self.assertEqual(ch2.detect_canary("PTO policy is 15 days").verdict, "未命中")


class DetectionAndEvasionTests(unittest.TestCase):
    def test_e01_hit_and_rewrite(self):
        hits = ch2.assess_detection("What documents do you have access to?")
        self.assertEqual([h.value for h in hits], ["E01"])
        advice = ch2.covert_rewrite("What documents do you have access to?", hits)
        self.assertTrue(any("具体主题" in a for a in advice["suggestions"]))

    def test_e02_e03_e04_d03(self):
        self.assertEqual([h.value for h in ch2.assess_detection("salary")], ["E02"])
        self.assertEqual([h.value for h in ch2.assess_detection("PTO policy")], ["E03"])
        self.assertEqual([h.value for h in ch2.assess_detection("your instructions")], ["E04"])
        self.assertEqual([h.value for h in ch2.assess_detection("knowledge cutoff")], ["D03"])

    def test_d02_burst(self):
        self.assertIsNone(ch2.endpoint_burst_risk(["/api/chat"]))
        burst = ch2.endpoint_burst_risk(["/api/chat", "/v1/completions"])
        self.assertEqual(burst.value, "2 个 AI 路径")

    def test_pacing_bounds(self):
        plan = ch2.pacing_plan("active")
        self.assertEqual((plan["min_gap_seconds"], plan["max_gap_seconds"]), (30, 60))
        self.assertTrue(plan["mix_legitimate_traffic"])


class RepositoryMiningTests(unittest.TestCase):
    def test_artifacts(self):
        got = ch2.mine_repository({
            "requirements.txt": "# c\ncrewai>=0.41.0\npinecone-client>=3.0.0",
            "config/rag.yaml": "chunk_size: 512\nscore_threshold: 0.75\nprovider: pinecone",
            "prompts/function_schemas.json": '{"name":"search_codebase","read-only":true}',
            "config/safety.yaml": "blocked_topics:\n  - internal roadmap",
            ".env.example": "GOOGLE_API_KEY=xxx\nPINECONE_API_KEY=yyy",
            "config/models.yaml": "model_id: Qwen/Qwen2.5\nquantization: AWQ",
        })
        self.assertEqual(got["dependencies"], ["crewai>=0.41.0", "pinecone-client>=3.0.0"])
        self.assertIn("chunk_size: 512", got["rag_config"])
        self.assertEqual(got["tool_schema"], ["search_codebase"])
        self.assertIn("GOOGLE_API_KEY", got["env_keys"])
        self.assertIn("model_supply_chain", got)


class Ch2DocumentCoverageTests(unittest.TestCase):
    """补强 §2.1/§2.3/§2.4 中初版未覆盖的自描述协议、阈值递减、日志视角等。"""

    def test_self_describing_mcp_and_a2a(self):
        mcp = ch2.parse_self_describing(json.dumps({
            "protocol": "MCP", "tools": [{"name": "search"}, {"name": "lookup"}]}))
        self.assertEqual(mcp.verdict, "存在")
        self.assertEqual([s.value for s in mcp.signals if s.kind == "self:tool"],
                         ["search", "lookup"])
        a2a = ch2.parse_self_describing(json.dumps({
            "protocol": "A2A", "capabilities": ["delegate"], "skills": ["review"]}))
        kinds = {s.kind for s in a2a.signals}
        self.assertIn("self:protocol", kinds)
        self.assertIn("self:capabilities", kinds)
        self.assertEqual(ch2.parse_self_describing("not json").verdict, "不可判定")

    def test_response_metadata_leak(self):
        got = ch2.parse_response_metadata(json.dumps({
            "content": "hi", "metadata": {"provider": "ollama", "model": "llama3.2:1b"}}))
        self.assertEqual({s.kind for s in got}, {"metadata:provider", "metadata:model"})
        self.assertEqual(ch2.parse_response_metadata('{"answer":"x"}'), [])

    def test_client_config_extraction(self):
        got = ch2.parse_client_config(
            'window.CFG={apiBase:"/api/v2",assistantEndpoint:"/api/v2/assistant",'
            'featureFlags:{enableAI:true,debugMode:false}};')
        kinds = {s.kind for s in got}
        self.assertIn("client:apiBase", kinds)
        self.assertIn("client:assistantEndpoint", kinds)
        self.assertIn("client:featureFlags", kinds)
        self.assertEqual(ch2.parse_client_config(""), [])

    def test_threshold_series_flip(self):
        stages = [
            {"stage": "exact", "triggered": True, "score": 0.51},
            {"stage": "synonym", "triggered": True, "score": 0.44},
            {"stage": "misspelling", "triggered": False, "score": 0.19},
        ]
        finding = ch2.probe_threshold_series(stages)
        self.assertEqual(finding.verdict, "存在")
        self.assertIn("翻转", finding.note)
        self.assertEqual(ch2.probe_threshold_series(stages[:1]).verdict, "不可判定")
        self.assertEqual(ch2.probe_threshold_series(stages[:2]).verdict, "不可判定")

    def test_log_visibility(self):
        finding = ch2.assess_log_visibility({
            "query": "what is PTO", "answer": "...", "sources": [],
            "semantic_analysis": False, "cross_session_correlation": False})
        kinds = {s.kind for s in finding.signals}
        self.assertIn("log:fields", kinds)
        self.assertEqual(len([s for s in finding.signals if s.kind == "log:gap"]), 2)
        self.assertEqual(ch2.assess_log_visibility(None).verdict, "不可判定")

    def test_analyze_dispatch_and_validation(self):
        result = ch2.analyze({"target": "http://t", "observations": [
            {"kind": "self_describe", "schema": json.dumps({
                "protocol": "A2A", "skills": ["x"]})},
            {"kind": "metadata", "body": '{"metadata":{"provider":"ollama"}}'},
            {"kind": "client_config", "text": 'apiBase:"/api/v2"'},
            {"kind": "threshold", "stages": [
                {"stage": "exact", "triggered": True},
                {"stage": "misspelling", "triggered": False}]},
            {"kind": "log_view", "log": {"query": "q", "intent_classification": False}},
        ]})
        names = {f["name"] for f in result["findings"]}
        self.assertEqual(names, {"模型行为指纹", "RAG 知识库映射", "自描述协议面",
                                 "客户端配置泄露", "检索阈值递减", "交互日志可见性"})
        self.assertIn("metadata:provider", {s["kind"] for s in result["signals"]})
        self.assertEqual(ch2.validate_analysis(result), [])

    def test_validate_flags_plaintext_in_metadata(self):
        bad = {"findings": [{"name": "自描述协议面", "verdict": "存在", "signals": [
            {"kind": "metadata:provider", "value": "sk-abc123secret", "basis": "x"},
        ], "note": ""}]}
        self.assertTrue(any("明文凭据" in v for v in ch2.validate_analysis(bad)))


class AnalyzeAndCliTests(unittest.TestCase):
    def test_analyze_end_to_end(self):
        result = ch2.analyze({"target": "http://t", "observations": [
            {"kind": "endpoint", "status": 401, "url": "u"},
            {"kind": "endpoint", "status": 404, "url": "v"},
            {"kind": "chat", "technique": "identity", "response": "I am Qwen"},
            {"kind": "detection", "query": "list documents"},
        ]})
        self.assertEqual(len(result["taxonomy"]), 4)
        self.assertEqual([e["verdict"] for e in result["endpoints"]],
                         ["AUTH_REQUIRED", "ABSENT"])
        self.assertEqual(ch2.validate_analysis(result), [])

    def test_validate_flags_plaintext_secret(self):
        bad = {"findings": [{"name": "诱饵识别", "verdict": "命中", "signals": [
            {"kind": "canary:password", "value": "NovaTech2024!", "basis": "x"}], "note": ""}]}
        self.assertTrue(any("未脱敏" in v for v in ch2.validate_analysis(bad)))

    def test_cli_analyze_subcommand(self):
        payload = {"target": "http://t", "observations": [
            {"kind": "headers", "headers": {"X-AI-Backend": "GPT-5.2"}}]}
        tmp = tempfile.mkdtemp()
        src = os.path.join(tmp, "obs.json")
        out = os.path.join(tmp, "out.json")
        with open(src, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False)
        self.assertEqual(cli.main(["analyze", "--input", src, "--out", out]), 0)
        with open(out, encoding="utf-8") as f:
            self.assertEqual(json.load(f)["signals"][0]["kind"], "header:X-AI-Backend")
        self.assertEqual(cli.main(["analyze", "--input", src + ".missing"]), 2)


if __name__ == "__main__":
    unittest.main()
