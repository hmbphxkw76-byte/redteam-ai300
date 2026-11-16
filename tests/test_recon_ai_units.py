#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""recon-ai 单元测试（S2）：CLI 契约、真实传输、截图能力、解析边界。

与 `test_recon_ai.py`（验收条件）互补：本文件覆盖入口层与 IO 适配层，
使行覆盖率达到 CI S2 门槛（≥80%）。
"""
import json
import os
import sys
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer
from types import SimpleNamespace
from unittest import mock

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from tools.recon_ai import cli, fingerprint, probes, shot, transport  # noqa: E402
from tools.recon_ai import runner as runner_mod  # noqa: E402
from tools.recon_ai.model import Asset, AssetInventory, Category, Existence  # noqa: E402


class _Handler(BaseHTTPRequestHandler):
    """本地回环服务：验证真实 urllib 传输的成功 / 4xx / 回显语义。"""

    def _send(self, code, body, ctype="application/json"):
        payload = body.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def do_GET(self):
        if self.path == "/ok":
            self._send(200, '{"ok":true}')
        elif self.path == "/missing":
            self._send(404, '{"detail":"Not Found"}')
        else:
            self._send(200, "<!doctype html><html></html>", "text/html")

    def do_POST(self):
        length = int(self.headers.get("Content-Length") or 0)
        body = self.rfile.read(length).decode("utf-8")
        self._send(200, body)

    def log_message(self, *args):
        return


class UrllibTransportTests(unittest.TestCase):
    """真实传输：仅本地回环，不触外网。"""

    @classmethod
    def setUpClass(cls):
        cls.server = HTTPServer(("127.0.0.1", 0), _Handler)
        cls.port = cls.server.server_port
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.base = "http://127.0.0.1:%d" % cls.port

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()

    def setUp(self):
        self.client = transport.UrllibTransport()

    def test_get_success(self):
        resp = self.client.request("GET", self.base + "/ok", timeout=5)
        self.assertEqual(resp.status, 200)
        self.assertTrue(resp.ok)
        self.assertTrue(resp.is_json)
        self.assertIn("ok", resp.body)

    def test_http_error_body_is_captured(self):
        resp = self.client.request("GET", self.base + "/missing", timeout=5)
        self.assertEqual(resp.status, 404)
        self.assertFalse(resp.ok)
        self.assertIn("Not Found", resp.body)

    def test_post_echoes_json_body(self):
        resp = self.client.request("POST", self.base + "/echo", {"prompt": "hi"}, timeout=5)
        self.assertIn("prompt", resp.body)

    def test_connection_error_is_not_exception(self):
        resp = self.client.request("GET", "http://127.0.0.1:1/", timeout=2)
        self.assertEqual(resp.status, 0)
        self.assertTrue(resp.error)

    def test_describe(self):
        self.assertIn("urllib", self.client.describe())


class FakeTransportTests(unittest.TestCase):
    def test_exact_and_prefix_and_default(self):
        env = transport.FakeTransport({
            ("GET", "http://x/api/config"): transport.HttpResponse(200, "{}"),
            ("GET", "http://x/assets/*"): transport.HttpResponse(200, "js"),
        })
        self.assertEqual(env.request("GET", "http://x/api/config").status, 200)
        self.assertEqual(env.request("GET", "http://x/assets/a.js").body, "js")
        self.assertEqual(env.request("GET", "http://x/none").status, 404)
        self.assertIn("fake", env.describe())

    def test_callable_route(self):
        env = transport.FakeTransport({
            ("POST", "http://x/e"): lambda body: transport.HttpResponse(200, json.dumps(body or {})),
        })
        self.assertIn("a", env.request("POST", "http://x/e", {"a": 1}).body)


class ShotTests(unittest.TestCase):
    def test_render_transcript_escapes_html(self):
        html = shot.render_transcript("curl <x>", "<script>alert(1)</script>", "http://t")
        self.assertIn("&lt;x&gt;", html)
        self.assertNotIn("<script>alert(1)</script>", html)

    def test_null_and_fake_capture(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(shot.NullShot().capture("s", "u", tmp), ("", ""))
            path, kind = shot.FakeShot().capture("s", "u", tmp)
            self.assertEqual(kind, "url")
            self.assertTrue(os.path.isfile(path))

    def test_headless_without_browser_is_honest_noop(self):
        capture = shot.HeadlessShot(browser_path="")
        capture.browser = ""
        self.assertEqual(capture.capture("s", "u", tempfile.gettempdir()), ("", ""))
        self.assertIn("none", capture.describe())

    def test_headless_falls_back_to_cdp_when_native_screenshot_fails(self):
        def fake_run(cmd, **kwargs):
            if "--screenshot=" in " ".join(cmd):
                return mock.Mock(returncode=0)
            with open(cmd[4], "wb") as f:
                f.write(b"\x89PNG\r\n\x1a\nCDP" + b"IEND\xaeB`\x82")
            return mock.Mock(returncode=0)

        with tempfile.TemporaryDirectory() as tmp:
            capture = shot.HeadlessShot(browser_path="browser.exe", node_path="node")
            with mock.patch.object(shot.subprocess, "run", side_effect=fake_run):
                path, kind = capture.capture("s", "http://t", tmp)
        self.assertEqual(kind, "url")
        self.assertTrue(path.endswith("s-url.png"))

    def test_cdp_disabled_without_node(self):
        capture = shot.HeadlessShot(browser_path="browser.exe", node_path="")
        with mock.patch.object(shot.subprocess, "run",
                               return_value=mock.Mock(returncode=0)) as run:
            with tempfile.TemporaryDirectory() as tmp:
                self.assertEqual(capture.capture("s", "http://t", tmp), ("", ""))
        self.assertEqual(run.call_count, 2)  # 原生路径重试两次，未启用 CDP

    def test_url_capture_falls_back_to_transcript_page(self):
        def fake_run(cmd, **kwargs):
            joined = " ".join(cmd)
            if joined.startswith("browser.exe") and cmd[-1].startswith("http"):
                return mock.Mock(returncode=1)
            out = [c for c in cmd if c.startswith("--screenshot=")][0].split("=", 1)[1]
            with open(out, "wb") as f:
                f.write(b"\x89PNG\r\n\x1a\nFB" + b"IEND\xaeB`\x82")
            return mock.Mock(returncode=0)

        with tempfile.TemporaryDirectory() as tmp:
            capture = shot.HeadlessShot(browser_path="browser.exe", node_path="")
            with mock.patch.object(shot.subprocess, "run", side_effect=fake_run):
                path, kind = capture.capture(
                    "s", "http://t", tmp, command="curl http://t", response="denied")
        self.assertEqual(kind, "transcript")
        self.assertTrue(path.endswith("s-transcript.png"))

    def test_make_shot_respects_switch(self):
        self.assertEqual(shot.make_shot(enabled=False).describe(), "none")

    def test_find_browser_honours_env(self):
        with tempfile.NamedTemporaryFile(suffix=".exe", delete=False) as tmp:
            name = tmp.name
        try:
            with mock.patch.dict(os.environ, {"RECON_AI_BROWSER": name}):
                self.assertEqual(shot.find_browser(), name)
        finally:
            os.remove(name)


class BaseTargetTests(unittest.TestCase):
    def test_file_target_normalized_to_origin(self):
        self.assertEqual(runner_mod._base_target("http://h/reports/x.html"),
                         "http://h")
        self.assertEqual(runner_mod._base_target("http://h/chat"), "http://h/chat")


class FingerprintTests(unittest.TestCase):
    @staticmethod
    def _result(body, content_type="application/javascript"):
        return runner_mod.ProbeResult(step_id="recon-03", url="http://t/bundle.js",
                                      status=200, body=body, content_type=content_type)

    def test_frontend_identifier_embedding_id_is_not_rag(self):
        # Streamlit 前端包中的 embeddingId 是普通标识符，不构成 RAG 痕迹
        self.assertIsNone(fingerprint.primary(self._result("var embeddingId=1;"),
                                              Category.RAG))

    def test_embedding_model_is_rag(self):
        match = fingerprint.primary(self._result('{"embedding_model":"bge-m3"}'),
                                    Category.RAG)
        self.assertIsNotNone(match)

    def test_retrieved_knowledge_is_rag(self):
        self.assertIsNotNone(fingerprint.primary(
            self._result("var retrieved_knowledge=1;"), Category.RAG))


class ProbeParsingTests(unittest.TestCase):
    def test_parse_sse_handles_malformed_and_mcp(self):
        body = ('event: meta\ndata: {"request_id":"r"}\n\n'
                'data: not-json\n\n'
                'data: {"mcpResult":{"tool":"x"}}\n\n')
        view = probes.parse_sse(body)
        self.assertIn("meta", view.events)
        self.assertEqual(view.meta.get("request_id"), "r")
        self.assertEqual(view.mcp_results, 1)
        self.assertIn("not-json", view.text)

    def test_curl_command_get_and_post(self):
        self.assertEqual(probes.curl_command("GET", "http://t/x"), "curl -s http://t/x")
        post = probes.curl_command("POST", "http://t/x", {"a": 1})
        self.assertIn("-X POST", post)
        self.assertIn("Content-Type", post)

    def test_mcp_judge_422_branch_and_guardrail_without_chat(self):
        schema = runner_mod.ProbeResult(step_id="recon-06", url="u", status=422,
                                        body='{"detail":[{"loc":["body","labId"]}]}')
        judgement = probes.judge_mcp([schema], {})
        self.assertEqual(judgement.existence, Existence.PRESENT)
        self.assertIn("422", judgement.note)
        self.assertEqual(probes.judge_guardrail([], {}).existence, Existence.UNDETERMINED)

    def test_mcp_judge_aggregates_every_alive_port(self):
        results = [
            runner_mod.ProbeResult(
                step_id="recon-06", url="http://t:7010/mcp/tools", status=200,
                body='{"tools":[{"name":"read_file"}]}',
                headers={"Access-Control-Allow-Origin": "*"}),
            runner_mod.ProbeResult(
                step_id="recon-06", url="http://t:7011/mcp/tools", status=200,
                body='{"tools":[{"name":"query_database"},{"name":"get_user"}]}'),
            runner_mod.ProbeResult(
                step_id="recon-06", url="http://t:7012/mcp/tools", status=0,
                error="refused"),
        ]
        judgement = probes.judge_mcp(results, {})
        self.assertEqual(judgement.existence, Existence.PRESENT)
        self.assertIn(":7010", judgement.note)
        self.assertIn(":7011", judgement.note)
        self.assertNotIn(":7012", judgement.note)
        self.assertEqual(judgement.context.get("endpoints"),
                         ["http://t:7010/mcp/tools", "http://t:7011/mcp/tools"])

    def test_streamlit_guardrail_records_websocket_gap(self):
        chat = runner_mod.ProbeResult(
            step_id="recon-02", url="http://t/chat/", status=200,
            body="<html><script src=\"static/js/main.js\"></script></html>",
            content_type="text/html")
        plan = SimpleNamespace(family="streamlit", signals=["chat_entry"])
        judgement = probes.judge_guardrail([chat], {"reuse_chat": chat, "plan": plan})
        self.assertEqual(judgement.existence, Existence.UNDETERMINED)
        self.assertIn("WebSocket", judgement.note)
        self.assertIn("聊天入口", judgement.note)

    def test_vector_judge_active_all_closed(self):
        closed = [runner_mod.ProbeResult(step_id="recon-04", url="http://h:%d/" % p,
                                         status=0, error="refused", note="port-probe")
                  for p in (6333, 8080)]
        judgement = probes.judge_vector(closed, {"profile": "active"})
        self.assertEqual(judgement.existence, Existence.ABSENT)

    def test_vector_judge_active_finds_alive_port(self):
        alive = [runner_mod.ProbeResult(step_id="recon-04", url="http://h:6333/",
                                        status=200, body='{"status":"ok"}',
                                        content_type="application/json", note="port-probe")]
        judgement = probes.judge_vector(alive, {"profile": "active"})
        self.assertEqual(judgement.existence, Existence.PRESENT)

    def test_missing_security_headers(self):
        self.assertEqual(len(probes.missing_security_headers({})), 6)
        self.assertEqual(len(probes.missing_security_headers(
            {"Content-Security-Policy": "x"})), 5)


class CliTests(unittest.TestCase):
    """CLI 契约：退出码、默认子命令、JSON 摘要。"""

    def _report(self):
        inv = AssetInventory.create(
            target="http://t", profile="passive",
            assets=[Asset("ai-llm-t-01", "LLM引擎", "LongCat-2.5", "2.5",
                          "http://t/api/config", "无", "recon-01")])
        return runner_mod.RunReport(
            target="http://t", profile="passive", started="s", finished="f",
            inventory=inv, judgements={"recon-01": mock.Mock(
                existence=Existence.PRESENT, product="LongCat-2.5")},
            evidence_paths=["/tmp/recon-01.md"], shots={}, failed_steps=[],
            warnings=[], manifest="m.jsonl", inventory_md="a.md",
            inventory_json="a.json", report_md="r.md",
            transport="fake", shot="fake", evidence_tool="collect_evidence.py")

    def test_run_subcommand_with_stub(self):
        with mock.patch.object(cli.runner, "run_recon", return_value=self._report()):
            self.assertEqual(cli.main(["run", "--target", "http://t"]), 0)

    def test_default_subcommand_and_json(self):
        with mock.patch.object(cli.runner, "run_recon", return_value=self._report()):
            self.assertEqual(cli.main(["--target", "http://t", "--json"]), 0)

    def test_inventory_subcommand(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "a.json")
            with open(path, "w", encoding="utf-8") as f:
                json.dump({"target": "t", "profile": "passive",
                           "assets": [{"asset_id": "a", "category": "c",
                                       "product": "p", "endpoint": "e"}]}, f)
            self.assertEqual(cli.main(["inventory", "--path", path]), 0)

    def test_inventory_read_error(self):
        self.assertEqual(cli.main(["inventory", "--path", "/nope/missing.json"]), 2)

    def test_invalid_profile_exits_2(self):
        with self.assertRaises(SystemExit) as ctx:
            cli.main(["run", "--target", "http://t", "--profile", "stealth"])
        self.assertEqual(ctx.exception.code, 2)

    def test_invalid_target_exits_2(self):
        self.assertEqual(cli.main(["run", "--target", "   "]), 2)

    def test_contract_violation_returns_1(self):
        report = self._report()
        report.inventory = AssetInventory.create(
            target="http://t", profile="passive",
            assets=[Asset("", "", "", "", "", "", "")])
        with mock.patch.object(cli.runner, "run_recon", return_value=report):
            self.assertEqual(cli.main(["run", "--target", "http://t"]), 1)


if __name__ == "__main__":
    unittest.main()
