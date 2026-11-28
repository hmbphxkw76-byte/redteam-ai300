#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""recon-05 A2A Agent Card 探针契约（阶段 9 / AC-RC-1、AC-RC-3）。

只断言外部行为：请求声明 + 判据输出，不断言内部实现细节。
"""
import json
import unittest

from tools.recon_ai import probes
from tools.recon_ai.model import Existence, ProbeResult

CARD = {
    "name": "A2A Orchestrator",
    "description": "Central orchestrator",
    "url": "http://0.0.0.0:8000",
    "protocolVersion": "0.2",
    "skills": [{"id": "workflow-planning", "name": "AI Workflow Planning"}],
}


def _results(card_body, status=200):
    return [
        ProbeResult("recon-05", "http://t/api/labs/DE_01/summary", status=404),
        ProbeResult("recon-05", "http://t/api/me/runs?limit=1", status=404),
        ProbeResult("recon-05", "http://t/.well-known/agent.json", status=status,
                    body=card_body, content_type="application/json"),
    ]


class ReconA2ATests(unittest.TestCase):
    def test_recon05_declares_agent_card_probe(self):
        spec = probes.find("recon-05")
        self.assertIn("/.well-known/agent.json",
                      [probes.request_path(r, {}) for r in spec.requests])

    def test_agent_card_alone_is_present(self):
        verdict = probes.judge_agent(_results(json.dumps(CARD)), {})
        self.assertEqual(verdict.existence, Existence.PRESENT)
        self.assertIn("Agent Card", verdict.product)
        self.assertIn("skills", verdict.note)
        self.assertEqual(verdict.context.get("agent_card", {}).get("name"),
                         "A2A Orchestrator")

    def test_request_id_signal_precedes_card(self):
        results = _results(json.dumps(CARD))
        results[0] = ProbeResult("recon-05", "http://t/api/labs/DE_01/summary",
                                 status=422, body='{"detail":[{"request_id":"abc"}]}')
        verdict = probes.judge_agent(results, {})
        self.assertEqual(verdict.signature, "request_id schema")
        self.assertNotIn("agent_card", verdict.context)

    def test_bad_card_does_not_claim_presence(self):
        verdict = probes.judge_agent(_results("not-json"), {})
        self.assertNotEqual(verdict.existence, Existence.PRESENT)

    def test_404_card_does_not_claim_presence(self):
        verdict = probes.judge_agent(_results(json.dumps(CARD), status=404), {})
        self.assertNotEqual(verdict.existence, Existence.PRESENT)


def _results_v2(card_body, status=200):
    """仅新版 A2A 规范路径（agent-card.json）应答、旧路径 404 的目标形态。"""
    return [
        ProbeResult("recon-05", "http://t/api/labs/DE_01/summary", status=404),
        ProbeResult("recon-05", "http://t/api/me/runs?limit=1", status=404),
        ProbeResult("recon-05", "http://t/.well-known/agent.json", status=404),
        ProbeResult("recon-05", "http://t/.well-known/agent-card.json", status=status,
                    body=card_body, content_type="application/json"),
    ]


class AgentCardV2Tests(unittest.TestCase):
    def test_recon05_declares_agent_card_v2_probe(self):
        spec = probes.find("recon-05")
        self.assertIn("/.well-known/agent-card.json",
                      [probes.request_path(r, {}) for r in spec.requests])

    def test_v2_card_alone_is_present(self):
        verdict = probes.judge_agent(_results_v2(json.dumps(CARD)), {})
        self.assertEqual(verdict.existence, Existence.PRESENT)
        self.assertIn("Agent Card", verdict.product)
        self.assertIn("agent-card.json", verdict.signature)
        self.assertEqual(verdict.context.get("agent_card", {}).get("name"),
                         "A2A Orchestrator")

    def test_v2_card_protocol_version_from_supported_interfaces(self):
        card = {k: v for k, v in CARD.items() if k != "protocolVersion"}
        card["supportedInterfaces"] = [{"protocolBinding": "JSONRPC",
                                        "protocolVersion": "1.0"}]
        verdict = probes.judge_agent(_results_v2(json.dumps(card)), {})
        self.assertEqual(verdict.context.get("agent_card", {}).get("protocol_version"),
                         "1.0")

    def test_v2_bad_card_does_not_claim_presence(self):
        verdict = probes.judge_agent(_results_v2("not-json"), {})
        self.assertNotEqual(verdict.existence, Existence.PRESENT)


if __name__ == "__main__":
    unittest.main()
