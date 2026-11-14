#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""attack-mcp-tool 单元级测试：截图缝、传输缝、值对象与本地 server 分支。

这些用例只覆盖「外部可观察的降级与错误行为」——无浏览器、不可达端点、
未知方法等，避免把内部实现锁死。
"""
import json
import os
import sys
import tempfile
import unittest
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from tools.attack_mcp_tool import model, poison, shot  # noqa: E402
from tools.attack_mcp_tool.mcp import jsonrpc_endpoint, site_base, api_base  # noqa: E402
from tools.attack_mcp_tool.steps import steps_for_paths  # noqa: E402
from tools.attack_mcp_tool.transport import (FakeHttpClient, HttpResponse,  # noqa: E402
                                            UrllibHttpClient)


class ShotTests(unittest.TestCase):
    """AC-13 相关：截图降级与转录页内容。"""

    def test_render_transcript_contains_target_and_timestamp(self):
        html = shot.render_transcript("curl x", "resp", "http://t.example",
                                      "2026-11-14T22:00:00+08:00", "mcp-01")
        self.assertIn("http://t.example", html)
        self.assertIn("2026-11-14T22:00:00+08:00", html)
        self.assertIn("mcp-01", html)

    def test_render_transcript_escapes_html(self):
        html = shot.render_transcript("<script>", "<b>x</b>", "u", "t")
        self.assertNotIn("<script>", html)
        self.assertIn("&lt;script&gt;", html)

    def test_null_capture_returns_empty(self):
        self.assertEqual(shot.NullCapture().capture("mcp-01", "u", "/tmp"), ("", ""))
        self.assertEqual(shot.NullCapture().describe(), "none")

    def test_fake_capture_writes_png(self):
        with tempfile.TemporaryDirectory() as tmp:
            path, kind = shot.FakeCapture().capture("mcp-01", "u", tmp)
            self.assertTrue(os.path.isfile(path))
            self.assertEqual(kind, "transcript")

    def test_headless_without_browser_degrades(self):
        capture = shot.HeadlessCapture(browser_path="")
        capture.browser = ""
        self.assertEqual(capture.capture("mcp-01", "u", "."), ("", ""))
        self.assertIn("none", capture.describe())

    def test_headless_with_non_producing_binary_returns_empty(self):
        with tempfile.TemporaryDirectory() as tmp:
            capture = shot.HeadlessCapture(browser_path=sys.executable)
            path, kind = capture.capture("mcp-01", "http://t.example", tmp,
                                         command="curl", response="r", timestamp="t")
            self.assertEqual((path, kind), ("", ""))
            self.assertEqual([n for n in os.listdir(tmp) if n.endswith(".html")], [],
                             "临时转录页必须被清理")

    def test_make_capture_disabled(self):
        self.assertIsInstance(shot.make_capture(False), shot.NullCapture)


class TransportTests(unittest.TestCase):
    def test_fake_client_returns_configured_response(self):
        client = FakeHttpClient({("GET", "http://t.example/x"):
                                 HttpResponse(status=200, body="ok")})
        self.assertEqual(client.request("GET", "http://t.example/x").body, "ok")
        self.assertEqual(client.describe(), "fake (1 routes)")

    def test_fake_client_prefix_route_and_default(self):
        client = FakeHttpClient({("POST", "http://t.example/api/*"):
                                 HttpResponse(status=201, body="prefix")},
                                default=HttpResponse(status=500, body="fallback"))
        self.assertEqual(client.request("POST", "http://t.example/api/labs").status, 201)
        self.assertEqual(client.request("GET", "http://elsewhere").status, 500)

    def test_fake_client_without_route_reports_connection_error(self):
        resp = FakeHttpClient().request("POST", "http://t.example")
        self.assertIn("连接失败", resp.error)
        self.assertFalse(resp.ok)

    def test_urllib_client_network_error_is_captured_not_raised(self):
        resp = UrllibHttpClient().request("GET", "http://127.0.0.1:9/none", timeout=2)
        self.assertTrue(resp.error)
        self.assertEqual(resp.status, 0)

    def test_urllib_client_handles_http_error_status(self):
        resp = UrllibHttpClient().request("POST", "http://192.168.40.189/api/labs",
                                          json_body={"x": 1}, timeout=5)
        if resp.error:  # 目标不可达时跳过（环境相关，不制造假阴性）
            self.skipTest("演练目标不可达：%s" % resp.error)
        self.assertIn(resp.status, (404, 405, 422))


class ModelTests(unittest.TestCase):
    def test_find_secrets_and_redact(self):
        text = '{"token": "sk-abcdefghij0123456789", "again": "sk-abcdefghij0123456789"}'
        found = model.find_secrets(text)
        self.assertEqual(found, ["sk-abcdefghij0123456789"])
        self.assertIn("<REDACTED>", model.redact(found[0]))
        self.assertEqual(model.redact(""), "")

    def test_surface_helpers(self):
        surface = model.ToolSurface(tools=(model.ToolDescriptor("a", scope="read"),))
        self.assertEqual(surface.names(), ("a",))
        self.assertEqual(surface.by_name("a").scope, "read")
        self.assertIsNone(surface.by_name("zzz"))
        self.assertEqual(surface.as_dict()["tools"][0]["name"], "a")

    def test_observation_payload_redacts_secret_index_only(self):
        """报告策略：`secrets` 索引脱敏（便于日志流转），`tool_result` 保留原文。

        原文必须保留——它是取证与面板提交的唯一依据（GOVERNANCE §6.1）；
        脱敏只作用于汇总索引，避免同一凭据在日志里多处散落。
        """
        obs = model.Observation(tool_result="sk-abcdefghij0123456789")
        payload = obs.as_dict()
        self.assertTrue(payload["secrets"][0].endswith("89"))
        self.assertIn("<REDACTED>", payload["secrets"][0])
        self.assertEqual(payload["tool_result"], "sk-abcdefghij0123456789")

    def test_has_admin_scope_variants(self):
        self.assertTrue(model.has_admin_scope({"permissions_used": ["admin"]}))
        self.assertTrue(model.has_admin_scope({"permissions_used": ["write:file"]}))
        self.assertTrue(model.has_admin_scope({}, {"t": "admin"}, "t"))
        self.assertFalse(model.has_admin_scope({"permissions_used": ["read"]}))

    def test_parse_tool_entries_ignores_table_header(self):
        text = "| Tool Name | Scope |\n|---|---|\n| `run_command` | `write` |"
        entries = model.parse_tool_entries(text)
        self.assertEqual([e["name"] for e in entries], ["run_command"])

    def test_url_helpers(self):
        self.assertEqual(api_base("http://h/explore"), "http://h/api")
        self.assertEqual(site_base("http://h/explore"), "http://h")
        self.assertEqual(jsonrpc_endpoint("http://h"), "http://h/mcp")
        self.assertEqual(jsonrpc_endpoint("http://h/custom"), "http://h/custom")


class ServerBranchTests(unittest.TestCase):
    def test_get_tools_list_endpoint(self):
        with poison.PoisonedMcpServer() as server:
            base = server.url.rsplit("/mcp", 1)[0]
            with urllib.request.urlopen(base + "/tools/list", timeout=5) as resp:
                data = json.loads(resp.read().decode("utf-8"))
        self.assertGreaterEqual(len(data["tools"]), 2)

    def test_unknown_method_and_unknown_tool(self):
        with poison.PoisonedMcpServer() as server:
            client = __import__("tools.attack_mcp_tool.transport",
                                fromlist=["UrllibHttpClient"]).UrllibHttpClient()
            from tools.attack_mcp_tool.mcp import JsonRpcMcpClient
            rpc = JsonRpcMcpClient(client, server.url)
            self.assertIn("协议错误", rpc.call_tool("no_such_tool").error)
            bad = client.request("POST", server.url,
                                 json_body={"jsonrpc": "2.0", "id": 1, "method": "x"})
            self.assertIn("Method not found", bad.body)

    def test_admin_and_command_tool_outputs(self):
        with poison.PoisonedMcpServer() as server:
            from tools.attack_mcp_tool.mcp import JsonRpcMcpClient
            rpc = JsonRpcMcpClient(UrllibHttpClient(), server.url)
            self.assertIn('"admin": true', rpc.call_tool("admin_action").tool_result)
            self.assertIn("id; whoami", rpc.call_tool("run_command",
                                                      {"cmd": "id; whoami"}).tool_result)


class StepSelectionTests(unittest.TestCase):
    def test_subset_paths_and_step(self):
        ids = [s.step_id for s in steps_for_paths(("A",))]
        self.assertEqual(ids[0], "mcp-01")
        self.assertEqual(ids[-1], "mcp-08")
        self.assertNotIn("mcp-05", ids)
        self.assertEqual([s.step_id for s in steps_for_paths((), "mcp-05")], ["mcp-05"])

    def test_unknown_step_raises(self):
        with self.assertRaises(ValueError):
            steps_for_paths((), "mcp-42")


if __name__ == "__main__":
    unittest.main()
