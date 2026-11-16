#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""路径 A 测试（infra-01..03）：面发现 / 云存储 / 模型服务器。

对齐 AC-03/05/06/07/08/18。
"""
import json
import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from tools.attack_infra import path_a  # noqa: E402
from tools.attack_infra.command import CommandResult, FakeCommand  # noqa: E402
from tools.attack_infra.model import Outcome, RunContext  # noqa: E402
from tools.attack_infra.transport import FakeTransport, HttpResponse  # noqa: E402

OLLAMA_TAGS = json.dumps({"models": [{"name": "llama3.2:latest"}]})
SPA = HttpResponse(status=200, content_type="text/html; charset=utf-8",
                   body="<!doctype html><html></html>")


def _ctx(transport, **kwargs):
    base = dict(target="h", transport=transport, command=FakeCommand(),
                timeout=5, ports=(11434,))
    base.update(kwargs)
    return RunContext(**base)


class DiscoverTests(unittest.TestCase):
    def test_spa_fallback_yields_absent(self):
        """AC-03：全部 200 text/html → ABSENT(spa_fallback)，不判存在。"""
        fake = FakeTransport({}, default=SPA)
        verdict = path_a.discover(_ctx(fake))
        self.assertIs(verdict.outcome, Outcome.ABSENT)
        self.assertEqual(verdict.reason, "spa_fallback")
        self.assertEqual(verdict.findings, [])

    def test_network_failure_yields_absent_network(self):
        fake = FakeTransport({}, default=HttpResponse(error="refused"))
        verdict = path_a.discover(_ctx(fake))
        self.assertEqual(verdict.reason, "network")

    def test_ollama_hit_is_exposed(self):
        fake = FakeTransport({
            "GET http://h:11434/api/tags": HttpResponse(
                status=200, content_type="application/json", body=OLLAMA_TAGS),
        }, default=SPA)
        verdict = path_a.discover(_ctx(fake))
        self.assertIs(verdict.outcome, Outcome.EXPOSED_NO_AUTH)
        self.assertEqual(verdict.findings[0].endpoint.kind, "ollama")
        self.assertIn("ollama", verdict.summary)

    def test_auth_required_when_only_401(self):
        """AC-05：401/403 判 AUTH_REQUIRED 且保留状态码。"""
        fake = FakeTransport({}, default=HttpResponse(status=401))
        verdict = path_a.discover(_ctx(fake, ports=(10250,)))
        self.assertIs(verdict.outcome, Outcome.AUTH_REQUIRED)
        self.assertEqual(verdict.findings[0].endpoint.status, 401)

    def test_command_is_replayable_without_placeholders(self):
        """AC-18：命令可由技术读者直接执行，且不含 <...> 占位符。"""
        fake = FakeTransport({}, default=SPA)
        verdict = path_a.discover(_ctx(fake))
        self.assertIn("curl -s --noproxy '*'", verdict.command)
        self.assertNotIn("<", verdict.command)
        self.assertNotIn("> ", verdict.command)

    def test_output_lists_every_probed_url(self):
        fake = FakeTransport({}, default=SPA)
        verdict = path_a.discover(_ctx(fake))
        self.assertIn("http://h:11434/api/tags", verdict.output)
        self.assertIn("http://h:11434/v1/models", verdict.output)


class InventoryDiscoverTests(unittest.TestCase):
    def test_inventory_endpoint_on_unknown_port_is_probed(self):
        fake = FakeTransport({
            "GET http://h2:9999/v1/models": HttpResponse(
                status=200, content_type="application/json",
                body=json.dumps({"object": "list", "data": [{"id": "m"}]})),
        }, default=SPA)
        verdict = path_a.discover(_ctx(fake, inventory_endpoints=("h2:9999",)))
        self.assertIs(verdict.outcome, Outcome.EXPOSED_NO_AUTH)
        self.assertEqual(verdict.findings[0].endpoint.port, 9999)


class CloudTests(unittest.TestCase):
    def test_no_bucket_is_absent(self):
        verdict = path_a.cloud_misconfig(_ctx(FakeTransport({})))
        self.assertIs(verdict.outcome, Outcome.ABSENT)
        self.assertEqual(verdict.reason, "none_found")

    def test_no_bucket_documents_non_cloud_rationale(self):
        """C1：无 bucket 时产出可复现的「非云 AI 平台」判定依据。"""
        verdict = path_a.cloud_misconfig(_ctx(FakeTransport({})))
        self.assertIn("判定依据", verdict.output)
        self.assertIn("无云 AI 平台特征", verdict.output)

    def test_anonymous_listing_success(self):
        argv = ("aws", "s3", "ls", "s3://b", "--no-sign-request", "--recursive")
        cmd = FakeCommand({argv: CommandResult(code=0, stdout="2026-01-01 model.bin")})
        verdict = path_a.cloud_misconfig(_ctx(FakeTransport({}), command=cmd,
                                              buckets=("b",)))
        self.assertIs(verdict.outcome, Outcome.EXPOSED_NO_AUTH)
        self.assertIn("model.bin", verdict.output)

    def test_access_denied_is_auth_required(self):
        argv = ("aws", "s3", "ls", "s3://b", "--no-sign-request", "--recursive")
        cmd = FakeCommand({argv: CommandResult(code=1,
                                              stderr="AccessDenied")})
        verdict = path_a.cloud_misconfig(_ctx(FakeTransport({}), command=cmd,
                                              buckets=("b",)))
        self.assertIs(verdict.outcome, Outcome.AUTH_REQUIRED)
        self.assertEqual(verdict.reason, "forbidden")

    def test_missing_tool_is_absent(self):
        cmd = FakeCommand({}, default=CommandResult(code=127, stderr="not found: aws"))
        verdict = path_a.cloud_misconfig(_ctx(FakeTransport({}), command=cmd,
                                              buckets=("b",)))
        self.assertEqual(verdict.reason, "no_tool")


class ModelServerTests(unittest.TestCase):
    def _routes(self):
        return {
            "GET http://h:11434/api/tags": HttpResponse(
                status=200, content_type="application/json", body=OLLAMA_TAGS),
            "POST http://h:11434/api/generate": HttpResponse(
                status=200, content_type="application/json",
                body=json.dumps({"response": "PWNED", "done": True})),
        }

    def test_no_model_server_is_absent(self):
        fake = FakeTransport({}, default=SPA)
        verdict = path_a.model_server(_ctx(fake))
        self.assertIs(verdict.outcome, Outcome.ABSENT)
        self.assertEqual(verdict.reason, "none_found")

    def test_unauthorised_listing_without_inference(self):
        fake = FakeTransport(self._routes(), default=SPA)
        verdict = path_a.model_server(_ctx(fake))
        self.assertIs(verdict.outcome, Outcome.EXPOSED_NO_AUTH)
        self.assertIn("llama3.2:latest", verdict.summary + verdict.output)
        self.assertNotIn("POST", fake.methods(), "AC-07：未开启开关不得发推理请求")

    def test_inference_flag_yields_exploited(self):
        fake = FakeTransport(self._routes(), default=SPA)
        verdict = path_a.model_server(_ctx(fake, allow_inference=True))
        self.assertIs(verdict.outcome, Outcome.EXPLOITED)
        self.assertIn("PWNED", verdict.output)

    def test_default_mode_never_writes(self):
        """AC-08：默认只读，方法白名单为 GET（推理关闭时）。"""
        fake = FakeTransport(self._routes(), default=SPA)
        path_a.model_server(_ctx(fake))
        self.assertEqual(set(fake.methods()), {"GET"})

    def test_empty_body_is_not_a_vllm_hit(self):
        """AC-03：`200` + 空体不得判为 vLLM（三元组要求结构命中）。"""
        fake = FakeTransport({
            "GET http://h:8000/v1/models": HttpResponse(status=200,
                                                        content_type="text/plain",
                                                        body=""),
        }, default=SPA)
        verdict = path_a.discover(_ctx(fake, ports=(8000,)))
        self.assertIs(verdict.outcome, Outcome.ABSENT)


if __name__ == "__main__":
    unittest.main()
