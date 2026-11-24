#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""目标画像解耦测试：证明同一 skill/tool 适配任意目标，且仅增配置即可扩展。

不触碰具体目标对象字面量作为断言基线；测试夹具自带两份异构目标画像。
"""
import json
import os
import sys
import tempfile
import unittest

from tests._paths import ROOT  # noqa: E402
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from tools import target_profile as tp  # noqa: E402
from tools.recon_ai import runner as recon_runner  # noqa: E402
from tools.attack_mcp_tool.steps import StepSpec  # noqa: E402
from tools.attack_mcp_tool.runner import _Session  # noqa: E402
from tools.attack_mcp_tool.model import AttackRequest  # noqa: E402

PROFILE_A = {
    "name": "alpha",
    "host": "alpha.example",
    "labs": {"chat": "CHAT_A", "vector": "VEC_A", "agent": "AGT_A",
             "mcp": "MCP_A", "MCP_01": "MCP_A"},
}
PROFILE_B = {
    "name": "beta",
    "host": "beta.internal",
    "labs": {"chat": "TALK_B", "vector": "VS_B", "agent": "AG_B",
             "mcp": "TOOL_B", "MCP_01": "TOOL_B"},
}


class ProfileRegistryTests(unittest.TestCase):
    def test_generic_default_is_all_placeholders(self):
        generic = tp.GENERIC
        self.assertEqual(generic.host, tp.PLACEHOLDER_HOST)
        self.assertEqual(generic.lab("chat"), tp.PLACEHOLDER_LAB)
        self.assertEqual(generic.endpoint("chat"), "/api/labs/{lab}/chat")

    def test_two_targets_resolve_from_config_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            config = os.path.join(tmp, "profiles.json")
            with open(config, "w", encoding="utf-8") as handle:
                json.dump({"profiles": [PROFILE_A, PROFILE_B]}, handle)
            alpha = tp.resolve("alpha", path=config)
            beta = tp.resolve("beta", path=config)
        self.assertEqual(alpha.host, "alpha.example")
        self.assertEqual(beta.host, "beta.internal")
        self.assertEqual(alpha.lab("vector"), "VEC_A")
        self.assertEqual(beta.lab("vector"), "VS_B")
        self.assertNotEqual(alpha.lab("chat"), beta.lab("chat"))

    def test_new_target_requires_only_config_file(self):
        """新增目标类型只加配置：核心模块源码不改动即可解析。"""
        with tempfile.TemporaryDirectory() as tmp:
            config = os.path.join(tmp, "delta.json")
            with open(config, "w", encoding="utf-8") as handle:
                json.dump({"profiles": [{
                    "name": "delta", "host": "delta.test",
                    "labs": {"chat": "D0", "mcp": "D1", "MCP_01": "D1"},
                    "extra": {"smb_hosts": ["fs.delta.test"]},
                }]}, handle)
            delta = tp.resolve("delta", path=config)
        self.assertEqual(delta.host, "delta.test")
        self.assertEqual(delta.map_lab("MCP_01"), "D1")
        self.assertEqual(delta.extra_list("smb_hosts"), ("fs.delta.test",))

    def test_unknown_profile_does_not_silently_fallback(self):
        with self.assertRaises(ValueError):
            tp.resolve("no-such-profile", path=os.path.join(ROOT, "tools", "target_profiles.json"))


class ReconAdapterTests(unittest.TestCase):
    def test_role_token_url_differs_across_targets(self):
        alpha = tp.from_mapping(PROFILE_A)
        beta = tp.from_mapping(PROFILE_B)
        path = "/api/labs/{lab:vector}/summary"
        url_a = recon_runner.build_url("http://a", path, alpha.lab("chat"),
                                       tp.role_labs(alpha))
        url_b = recon_runner.build_url("http://b", path, beta.lab("chat"),
                                       tp.role_labs(beta))
        self.assertEqual(url_a, "http://a/api/labs/VEC_A/summary")
        self.assertEqual(url_b, "http://b/api/labs/VS_B/summary")
        self.assertNotIn("{lab", url_a)

    def test_body_role_token_resolved(self):
        profile = tp.from_mapping(PROFILE_B)
        labs = tp.role_labs(profile)
        body = recon_runner.resolve_body({"labId": "{lab:mcp}"}, labs)
        self.assertEqual(body, {"labId": "TOOL_B"})


class McpAdapterTests(unittest.TestCase):
    def _session_lab(self, profile):
        request = AttackRequest(target="http://t", target_profile=profile)
        session = _Session.__new__(_Session)
        session.request = request
        spec = StepSpec("mcp-01", "A", "x", "y", lab="MCP_01")
        return session.lab(spec)

    def test_step_symbol_remapped_per_target(self):
        self.assertEqual(self._session_lab(tp.from_mapping(PROFILE_A)), "MCP_A")
        self.assertEqual(self._session_lab(tp.from_mapping(PROFILE_B)), "TOOL_B")


if __name__ == "__main__":
    unittest.main()
