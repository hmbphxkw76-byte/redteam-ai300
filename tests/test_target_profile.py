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
from unittest import mock

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


class ProfileHeadersTests(unittest.TestCase):
    """画像级请求头：令 Host 绑定类目标仅经配置适配，不落在命令行或代码里。"""

    def test_headers_roundtrip_and_default_empty(self):
        p = tp.from_mapping({"name": "h1", "headers": {"Host": "alias.example:8100"}})
        self.assertEqual(dict(p.headers), {"Host": "alias.example:8100"})
        self.assertEqual(dict(p.to_dict()["headers"]), {"Host": "alias.example:8100"})
        self.assertEqual(dict(tp.GENERIC.headers), {})

    def test_headers_must_be_mapping(self):
        with self.assertRaises(ValueError):
            tp.from_mapping({"name": "bad", "headers": "Host:alias"})

    def test_merged_headers_cli_overrides(self):
        p = tp.from_mapping({"name": "h2",
                             "headers": {"Host": "alias.example", "X-Prof": "1"}})
        self.assertEqual(dict(p.merged_headers({"Host": "cli.example"})),
                         {"Host": "cli.example", "X-Prof": "1"})
        self.assertEqual(dict(p.merged_headers()), {"Host": "alias.example",
                                                    "X-Prof": "1"})


class ProfilePathResolveTests(unittest.TestCase):
    """resolve 须兑现 CLI 帮助承诺：画像名或直接 JSON 文件/目录路径。"""

    def test_resolve_by_json_path(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "profiles.json")
            with open(path, "w", encoding="utf-8") as fh:
                json.dump({"profiles": [PROFILE_A]}, fh)
            self.assertEqual(tp.resolve(path).name, "alpha")

    def test_resolve_path_unknown_name_still_errors(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "profiles.json")
            with open(path, "w", encoding="utf-8") as fh:
                json.dump({"profiles": [PROFILE_A]}, fh)
            with self.assertRaises(ValueError):
                tp.resolve(os.path.join(d, "missing.json"))


class CliProfileHeaderTests(unittest.TestCase):
    """两个 CLI：画像 headers 自动进入请求头，--header 同名覆盖。"""

    def test_recon_cli_merges_profile_headers(self):
        from tools.recon_ai import cli as recon_cli
        captured = {}

        def fake_run_recon(*a, **k):
            captured.update(k)
            raise ValueError("STOP")

        with tempfile.TemporaryDirectory() as d:
            reg = os.path.join(d, "profiles.json")
            with open(reg, "w", encoding="utf-8") as fh:
                json.dump({"profiles": [{"name": "hp", "host": "hp.example",
                                         "headers": {"Host": "alias.example:8100",
                                                     "X-Prof": "1"}}]}, fh)
            with mock.patch.dict(os.environ, {tp.ENV_REGISTRY: reg}), \
                    mock.patch.object(recon_cli.runner, "run_recon", fake_run_recon):
                rc = recon_cli.main(["run", "--target", "http://hp.example:8100",
                                     "--target-profile", "hp", "--no-shots"])
            self.assertEqual(rc, 2)  # ValueError("STOP") → 用法错误出口
            self.assertEqual(captured.get("extra_headers"),
                             {"Host": "alias.example:8100", "X-Prof": "1"})

    def test_recon_cli_header_flag_overrides_profile(self):
        from tools.recon_ai import cli as recon_cli
        captured = {}

        def fake_run_recon(*a, **k):
            captured.update(k)
            raise ValueError("STOP")

        with tempfile.TemporaryDirectory() as d:
            reg = os.path.join(d, "profiles.json")
            with open(reg, "w", encoding="utf-8") as fh:
                json.dump({"profiles": [{"name": "hp", "host": "hp.example",
                                         "headers": {"Host": "alias.example:8100"}}]}, fh)
            with mock.patch.dict(os.environ, {tp.ENV_REGISTRY: reg}), \
                    mock.patch.object(recon_cli.runner, "run_recon", fake_run_recon):
                recon_cli.main(["run", "--target", "http://hp.example:8100",
                                "--target-profile", "hp", "--no-shots",
                                "--header", "Host: cli.example"])
            self.assertEqual(captured.get("extra_headers"), {"Host": "cli.example"})

    def test_mcp_cli_merges_profile_headers(self):
        from tools.attack_mcp_tool import cli as mcp_cli
        captured = {}

        def fake_client(extra_headers=None):
            captured["h"] = extra_headers
            return object()

        def fake_run_attack(request, runtime):
            raise ValueError("STOP")

        with tempfile.TemporaryDirectory() as d:
            reg = os.path.join(d, "profiles.json")
            with open(reg, "w", encoding="utf-8") as fh:
                json.dump({"profiles": [{"name": "hp", "host": "hp.example",
                                         "headers": {"Host": "alias.example:8100"}}]}, fh)
            with mock.patch.dict(os.environ, {tp.ENV_REGISTRY: reg}), \
                    mock.patch.object(mcp_cli, "UrllibHttpClient", fake_client), \
                    mock.patch.object(mcp_cli, "run_attack", fake_run_attack):
                rc = mcp_cli.main(["--target", "http://hp.example/mcp",
                                   "--mode", "jsonrpc", "--step", "mcp-01",
                                   "--no-emit", "--no-shot",
                                   "--target-profile", "hp"])
            self.assertEqual(rc, 2)
            self.assertEqual(captured.get("h"), {"Host": "alias.example:8100"})


if __name__ == "__main__":
    unittest.main()
