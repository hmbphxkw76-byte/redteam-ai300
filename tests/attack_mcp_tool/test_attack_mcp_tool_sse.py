#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""旧式 HTTP+SSE MCP 传输（legacy transport）契约测试。

3100 类网络型 MCP lab 走 GET 流 `event: endpoint` → POST `/messages?sessionId=`
收 202 → JSON-RPC 响应从流回收；本文件以注入式 stream_reader 全离线验证。
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
from tools.attack_mcp_tool import transport as tp_mod  # noqa: E402
from tools.attack_mcp_tool.mcp import JsonRpcMcpClient  # noqa: E402


def _session_lines(ids):
    lines = ["event: endpoint\n", "data: /messages?sessionId=s1\n", "\n"]
    for i in ids:
        if i == 2:
            lines.append('data: {"jsonrpc": "2.0", "id": 2, "result":'
                         ' {"tools": [{"name": "alpha"}]}}\n')
        else:
            lines.append('data: {"jsonrpc": "2.0", "id": %d, "result":'
                         ' {"protocolVersion": "2025-03-26"}}\n' % i)
    return lines


class McpSseTransportTests(unittest.TestCase):
    def _transport(self, ids=(1,), wait_timeout=2.0, endpoint=True):
        seen = {}

        def reader(url, headers=None, timeout=30):
            seen["url"] = url
            if endpoint:
                return iter(_session_lines(ids))
            return iter(["data: nope\n"])

        inner = tp_mod.FakeHttpClient(routes={
            ("POST", "http://t/messages?sessionId=s1"):
                tp_mod.HttpResponse(status=202, body=""),
        })
        tr = tp_mod.McpSseHttpClient(inner, stream_reader=reader,
                                     wait_timeout=wait_timeout)
        return tr, inner, seen

    def test_jsonrpc_post_routed_via_session_stream(self):
        tr, inner, seen = self._transport(ids=(1,))
        resp = tr.request("POST", "http://t/mcp",
                          json_body={"jsonrpc": "2.0", "id": 1,
                                     "method": "tools/list"})
        self.assertEqual(seen["url"], "http://t/mcp")
        self.assertTrue(resp.ok, resp.error)
        data = json.loads(resp.body)
        self.assertEqual(data["id"], 1)
        posted = [c for c in inner.calls if c["method"] == "POST"]
        self.assertEqual(posted[0]["url"], "http://t/messages?sessionId=s1")
        self.assertNotIn("http://t/mcp", [c["url"] for c in posted])

    def test_notification_returns_post_response(self):
        tr, inner, _ = self._transport(ids=(1,))
        resp = tr.request("POST", "http://t/mcp",
                          json_body={"jsonrpc": "2.0",
                                     "method": "notifications/initialized"})
        self.assertEqual(resp.status, 202)

    def test_non_jsonrpc_delegates_to_inner(self):
        tr, inner, _ = self._transport(ids=(1,))
        resp = tr.request("GET", "http://t/anything")
        self.assertTrue(resp.error)  # Fake 未配路由 → 连接失败形态
        self.assertEqual(inner.calls[-1]["method"], "GET")

    def test_missing_endpoint_times_out_with_error(self):
        tr, _, _ = self._transport(endpoint=False, wait_timeout=0.5)
        resp = tr.request("POST", "http://t/mcp",
                          json_body={"jsonrpc": "2.0", "id": 9,
                                     "method": "tools/list"})
        self.assertTrue(resp.error)
        self.assertNotEqual(resp.status, 200)

    def test_session_reused_across_calls(self):
        tr, _, seen = self._transport(ids=(1, 2))
        r1 = tr.request("POST", "http://t/mcp",
                        json_body={"jsonrpc": "2.0", "id": 1,
                                   "method": "initialize"})
        r2 = tr.request("POST", "http://t/mcp",
                        json_body={"jsonrpc": "2.0", "id": 2,
                                   "method": "tools/list"})
        self.assertTrue(r1.ok and r2.ok, (r1.error, r2.error))
        self.assertEqual(json.loads(r2.body)["result"]["tools"][0]["name"],
                         "alpha")
        self.assertEqual(seen["url"], "http://t/mcp")  # 仅建会话一次


class JsonRpcClientOverSseTests(unittest.TestCase):
    """协议层复用：JsonRpcMcpClient 对传输包装完全无感。"""

    def test_list_tools_through_sse_transport(self):
        def reader(url, headers=None, timeout=30):
            return iter(_session_lines((1, 2)))

        inner = tp_mod.FakeHttpClient(routes={
            ("POST", "http://t/messages?sessionId=s1"):
                tp_mod.HttpResponse(status=202, body=""),
        })
        client = JsonRpcMcpClient(
            tp_mod.McpSseHttpClient(inner, stream_reader=reader,
                                    wait_timeout=2.0), "http://t/mcp")
        surface, obs = client.list_tools()
        self.assertEqual(surface.names(), ("alpha",), obs.error)


class CliTransportSelectionTests(unittest.TestCase):
    """CLI：--mcp-transport sse 或画像 extra.mcp_transport 均可选择 SSE 传输。"""

    def _run(self, argv, profile_json=None):
        from tools.attack_mcp_tool import cli as mcp_cli
        captured = {}

        def fake_run_attack(request, runtime):
            captured["runtime"] = runtime
            raise ValueError("STOP")

        patches = [mock.patch.object(mcp_cli, "run_attack", fake_run_attack),
                   mock.patch.object(mcp_cli, "UrllibHttpClient",
                                     lambda extra_headers=None: "INNER")]
        env = {}
        if profile_json is not None:
            d = tempfile.mkdtemp()
            path = os.path.join(d, "p.json")
            with open(path, "w", encoding="utf-8") as fh:
                json.dump({"profiles": [profile_json]}, fh)
            env = {tp.ENV_REGISTRY: path, tp.ENV_PROFILE: profile_json["name"]}
        patches.append(mock.patch.dict(os.environ, env))
        with patches[0], patches[1], patches[2]:
            rc = mcp_cli.main(argv)
        return rc, captured

    def test_cli_flag_selects_sse(self):
        rc, cap = self._run(["--target", "http://t/mcp", "--mode", "jsonrpc",
                             "--step", "mcp-01", "--no-emit", "--no-shot",
                             "--mcp-transport", "sse"])
        self.assertEqual(rc, 2)
        client = cap["runtime"].client
        self.assertIsInstance(client, tp_mod.McpSseHttpClient)

    def test_default_keeps_plain_inner(self):
        rc, cap = self._run(["--target", "http://t/mcp", "--mode", "jsonrpc",
                             "--step", "mcp-01", "--no-emit", "--no-shot"])
        self.assertIs(cap["runtime"].client, "INNER")

    def test_profile_extra_selects_sse(self):
        rc, cap = self._run(
            ["--target", "http://t/mcp", "--mode", "jsonrpc",
             "--step", "mcp-01", "--no-emit", "--no-shot",
             "--target-profile", "ssex"],
            profile_json={"name": "ssex", "host": "sx.example",
                          "extra": {"mcp_transport": "sse"}})
        self.assertIsInstance(cap["runtime"].client, tp_mod.McpSseHttpClient)


if __name__ == "__main__":
    unittest.main()
