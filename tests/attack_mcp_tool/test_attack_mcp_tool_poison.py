#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""attack-mcp-tool 工具面枚举与投毒自证测试（规格 v2 AC-03/04/05/06/07）。

只断言外部可观测行为：解析出的工具面、SSE 事件归属、差分结构、真实本地 server
的枚举结果。不触碰私有实现细节。
"""
import json
import os
import sys
import unittest
import urllib.error
import urllib.request
from dataclasses import replace

from tests._paths import ROOT  # noqa: E402
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from tools.attack_mcp_tool import poison  # noqa: E402
from tools.attack_mcp_tool.mcp import (AgentSseClient, JsonRpcMcpClient,  # noqa: E402
                                      parse_sse)
from tools.attack_mcp_tool.model import ToolSurface  # noqa: E402
from tools.attack_mcp_tool.transport import FakeHttpClient, HttpResponse, UrllibHttpClient  # noqa: E402

TOOLS_LIST_RESPONSE = {
    "jsonrpc": "2.0", "id": 1,
    "result": {"tools": [
        {"name": "get_config", "description": "Get config", "_scope": "read",
         "_server_id": "main_server", "_trust": "trusted"},
        {"name": "run_command", "description": "Run a command", "_scope": "write",
         "_server_id": "exec_server", "_trust": "trusted"},
    ]},
}


def sse_meta_then_chunks(chunks, telemetry=None, tool_result=""):
    """构造与目标一致的 SSE 报文（meta + 分片 + 可选 mcp_result）。"""
    lines = ["event: meta",
             'data: {"request_id": "r-1", "lab_id": "MCP_01", "phase": 4}']
    for c in chunks:
        lines.append("")
        lines.append('data: {"content": %s}' % json.dumps(c, ensure_ascii=False))
    if tool_result:
        payload = {"tool_result": tool_result, "mcp_telemetry": telemetry or {}}
        lines.append("")
        lines.append("event: mcp_result")
        lines.append("data: %s" % json.dumps(payload, ensure_ascii=False))
    return "\n".join(lines) + "\n"


class SurfaceParsingTests(unittest.TestCase):
    """AC-03：JSON-RPC 工具面逐字段解析。"""

    def test_ac03_tools_list_fields(self):
        client = FakeHttpClient({("POST", "http://t.example/mcp"):
                                 HttpResponse(status=200, body=json.dumps(TOOLS_LIST_RESPONSE),
                                              content_type="application/json")})
        surface, obs = JsonRpcMcpClient(client, "http://t.example/mcp").list_tools()
        self.assertEqual([t.name for t in surface.tools], ["get_config", "run_command"])
        self.assertEqual(surface.tools[0].scope, "read")
        self.assertEqual(surface.tools[0].server_id, "main_server")
        self.assertEqual(surface.tools[0].trust, "trusted")
        self.assertEqual(surface.tools[1].scope, "write")
        self.assertFalse(obs.error)

    def test_stateful_mcp_session_handshake_and_sse_tools(self):
        """有状态 MCP：initialize 取会话 ID，后续请求沿用；SSE 响应可解析。"""
        def handler(req):
            method = (req or {}).get("method")
            if method == "initialize":
                body = ("event: message\ndata: " + json.dumps({
                    "jsonrpc": "2.0", "id": 1,
                    "result": {"protocolVersion": "2025-03-26"}}) + "\n\n")
                return HttpResponse(status=200, body=body,
                                    headers={"mcp-session-id": "sid-123"},
                                    content_type="text/event-stream")
            if method == "notifications/initialized":
                return HttpResponse(status=202, body="")
            if method == "tools/list":
                body = ("event: message\ndata: " + json.dumps({
                    "jsonrpc": "2.0", "id": 2,
                    "result": {"tools": [{"name": "alpha", "description": "d"}]}}
                ) + "\n\n")
                return HttpResponse(status=200, body=body,
                                    content_type="text/event-stream")
            return HttpResponse(status=404, body="")

        client = FakeHttpClient(default=handler)
        rpc = JsonRpcMcpClient(client, "http://t.example/mcp")
        surface, obs = rpc.list_tools()
        self.assertFalse(obs.error)
        self.assertEqual([t.name for t in surface.tools], ["alpha"])
        tools_call = [c for c in client.calls
                      if (c["json_body"] or {}).get("method") == "tools/list"][0]
        self.assertEqual(tools_call["headers"], {"Mcp-Session-Id": "sid-123"})
        methods = [(c["json_body"] or {}).get("method") for c in client.calls]
        self.assertIn("initialize", methods)
        self.assertIn("notifications/initialized", methods)

    def test_ac03_protocol_error_does_not_invent_tools(self):
        body = {"jsonrpc": "2.0", "id": 1, "error": {"code": -32601, "message": "nope"}}
        client = FakeHttpClient({("POST", "http://t.example/mcp"):
                                 HttpResponse(status=200, body=json.dumps(body))})
        surface, obs = JsonRpcMcpClient(client, "http://t.example/mcp").list_tools()
        self.assertEqual(surface.tools, ())
        self.assertIn("协议错误", obs.error)


class AgentSseTests(unittest.TestCase):
    """AC-04 / AC-05：SSE 解析与事件归属。"""

    def test_ac04_probe_extracts_text_result_and_telemetry(self):
        body = sse_meta_then_chunks(
            ["- **Tool name:** `get_config`  ", "**Required scope:** `read`"],
            telemetry={"selected_tool": "get_config", "trust_level": "trusted",
                       "exploit_success": True, "permissions_used": ["read"]},
            tool_result='{"service_token": "sk-abcdefghij0123456789"}')
        client = FakeHttpClient({("POST", "http://t.example/api/labs/MCP_01/chat"):
                                 HttpResponse(status=200, body=body,
                                              content_type="text/event-stream")})
        turn = AgentSseClient(client, "http://t.example").probe("MCP_01", "list tools")
        self.assertIn("get_config", turn.text)
        self.assertEqual(turn.telemetry().get("selected_tool"), "get_config")
        self.assertIn("service_token", turn.first_result.tool_result)
        self.assertTrue(turn.telemetry().get("exploit_success"))

    def test_ac05_event_scope_is_single_data_line(self):
        raw = ('event: meta\ndata: {"lab_id": "MCP_01"}\n'
               'data: {"content": "hi"}\ndata: {"content": " there"}\n')
        events = parse_sse(raw)
        self.assertEqual([e.name for e in events], ["meta", "message", "message"])
        self.assertEqual(events[1].obj.get("content"), "hi")

    def test_ac05_event_does_not_leak_across_blank_lines(self):
        raw = ('event: mcp_result\ndata: {"tool_result": "x"}\n\n'
               'data: {"content": "after"}\n')
        events = parse_sse(raw)
        self.assertEqual(events[0].name, "mcp_result")
        self.assertEqual(events[1].name, "message")


class PoisonSelfProofTests(unittest.TestCase):
    """AC-06 / AC-07：本地恶意 server 与投毒差分。"""

    def test_ac06_local_server_serves_poisoned_surface(self):
        with poison.PoisonedMcpServer() as server:
            client = JsonRpcMcpClient(UrllibHttpClient(), server.url)
            surface, obs = client.list_tools()
        self.assertFalse(obs.error)
        self.assertGreaterEqual(len(surface.tools), 2)
        self.assertTrue(any(poison.POISON_INSTRUCTION in t.description
                            for t in surface.tools),
                        "投毒工具面必须含隐藏指令")
        self.assertTrue(any(t.scope == "admin" for t in surface.tools),
                        "投毒工具面必须含被放大的权限声明")

    def test_ac06_call_tool_executes_attacker_arguments(self):
        with poison.PoisonedMcpServer() as server:
            client = JsonRpcMcpClient(UrllibHttpClient(), server.url)
            obs = client.call_tool("read_file", {"path": "/etc/hostname"})
        self.assertIn("/etc/hostname", obs.tool_result)

    def test_ac07_diff_has_three_keys_and_field_detail(self):
        diff = poison.diff_as_dict(poison.diff_surfaces(
            poison.baseline_surface(), poison.poisoned_surface()))
        self.assertEqual(set(diff), {"added", "removed", "changed"})
        self.assertIn("exfil_send", diff["added"])
        changed = {c["name"]: c["fields"] for c in diff["changed"]}
        self.assertIn("read_file", changed)
        self.assertIn("description", changed["read_file"])
        self.assertIn("scope", changed["read_file"])

    def test_ac07_no_change_means_empty_diff(self):
        surface = poison.baseline_surface()
        diff = poison.diff_as_dict(poison.diff_surfaces(surface, surface))
        self.assertEqual(diff, {"added": [], "removed": [], "changed": []})


class ServerHandlerEdgeTests(unittest.TestCase):
    """server 端点边界：404 / 解析错误 / 未知 method / 未知工具 / 生命周期。

    处理器运行在 ThreadingHTTPServer 的工作线程，故一律走真实 HTTP，
    不用进程内直调（避免把线程路径从覆盖与行为验证中排除）。
    """

    def setUp(self):
        self.server = poison.PoisonedMcpServer().start()
        self.addCleanup(self.server.stop)
        self.base = self.server.url.rsplit("/mcp", 1)[0]

    def _get(self, path):
        with urllib.request.urlopen(self.base + path, timeout=5) as resp:
            return resp.status, json.loads(resp.read().decode("utf-8"))

    def _post(self, payload):
        request = urllib.request.Request(
            self.base + "/mcp",
            data=payload if isinstance(payload, bytes) else json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"}, method="POST")
        try:
            with urllib.request.urlopen(request, timeout=5) as resp:
                return resp.status, json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            return exc.code, json.loads(exc.read().decode("utf-8"))

    def test_unknown_path_returns_404_detail(self):
        with self.assertRaises(urllib.error.HTTPError) as ctx:
            self._get("/nope")
        self.assertEqual(ctx.exception.code, 404)
        self.assertEqual(json.loads(ctx.exception.read().decode("utf-8")),
                         {"detail": "Not Found"})

    def test_root_and_trailing_slash_serve_same_surface(self):
        for path in ("/", "/tools/list", "/tools/list/"):
            with self.subTest(path=path):
                status, body = self._get(path)
                self.assertEqual(status, 200)
                self.assertEqual([t["name"] for t in body["tools"]],
                                 ["read_file", "exfil_send"])

    def test_malformed_json_returns_parse_error(self):
        status, body = self._post(b"{not json")
        self.assertEqual(status, 400)
        self.assertEqual(body["error"]["code"], -32700)

    def test_unknown_method_returns_method_not_found(self):
        status, body = self._post({"jsonrpc": "2.0", "id": 1, "method": "resources/list"})
        self.assertEqual(status, 200)
        self.assertEqual(body["error"]["code"], -32601)

    def test_unknown_tool_returns_invalid_params_with_name(self):
        status, body = self._post({"jsonrpc": "2.0", "id": 2, "method": "tools/call",
                                   "params": {"name": "ghost", "arguments": {}}})
        self.assertEqual(status, 200)
        self.assertEqual(body["error"]["code"], -32602)
        self.assertIn("ghost", body["error"]["message"])

    def test_stop_is_idempotent_even_without_start(self):
        idle = poison.PoisonedMcpServer()
        idle.stop()
        idle.stop()
        self.server.stop()
        self.server.stop()  # 重复 stop 不得抛异常（finally 里会再调一次）

    def test_shadow_schema_equal_detects_name_set_and_field_drift(self):
        baseline, shadow = poison.baseline_surface(), poison.shadow_surface()
        self.assertTrue(poison.shadow_schema_equal(baseline, shadow))
        subset = ToolSurface(tools=(), source="attacker_mcp:shadow")
        self.assertFalse(poison.shadow_schema_equal(baseline, subset),
                         "工具名集合不同必须判为不一致")
        drifted = ToolSurface(tools=(replace(shadow.tools[0], scope="admin"),),
                              source="attacker_mcp:shadow")
        self.assertFalse(poison.shadow_schema_equal(baseline, drifted),
                         "同名但权限字段不同必须判为不一致")

    def test_diff_reports_removed_tools_in_reverse_direction(self):
        diff = poison.diff_as_dict(poison.diff_surfaces(
            poison.poisoned_surface(), poison.baseline_surface()))
        self.assertIn("exfil_send", diff["removed"])
        self.assertEqual(diff["added"], [])


if __name__ == "__main__":
    unittest.main()
