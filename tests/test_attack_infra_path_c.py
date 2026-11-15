#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""路径 C 测试（infra-06..08）：提权归属 / 影响对照 / flag 双通道。

对齐 AC-11/12/13/14/17。
"""
import json
import os
import socket
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from tools.attack_infra import path_c  # noqa: E402
from tools.attack_infra.command import CommandResult, FakeCommand  # noqa: E402
from tools.attack_infra.model import Outcome, RunContext  # noqa: E402
from tools.attack_infra.transport import FakeTransport, HttpResponse  # noqa: E402

ENDPOINT = "http://h:11434/api/generate"


def _ctx(command=None, transport=None, **kwargs):
    base = dict(target="h", command=command or FakeCommand({}),
                transport=transport or FakeTransport({}), timeout=5,
                inference_endpoint=ENDPOINT)
    base.update(kwargs)
    return RunContext(**base)


def _body(response_text, created="2026-11-15T00:00:00Z", duration=100):
    return json.dumps({"model": "llama3.2:latest", "response": response_text,
                       "done": True, "created_at": created,
                       "total_duration": duration})


class PrivescTests(unittest.TestCase):
    def test_no_command_is_absent(self):
        verdict = path_c.privesc(_ctx())
        self.assertIs(verdict.outcome, Outcome.ABSENT)
        self.assertEqual(verdict.reason, "none_found")

    def test_local_echo_is_blocked(self):
        """AC-11：回显命中本机主机名/用户名 → BLOCKED(local_echo)。"""
        cmd = FakeCommand({"id": CommandResult(
            code=0, stdout="uid=1000(%s) gid=1000" % socket.gethostname())})
        verdict = path_c.privesc(_ctx(command=cmd, exec_argv=("id",)))
        self.assertIs(verdict.outcome, Outcome.BLOCKED)
        self.assertEqual(verdict.reason, "local_echo")

    def test_remote_echo_is_exploited(self):
        cmd = FakeCommand({"id": CommandResult(
            code=0, stdout="uid=0(root) gid=0(root) groups=0(root)")})
        verdict = path_c.privesc(_ctx(command=cmd, exec_argv=("id",)))
        self.assertIs(verdict.outcome, Outcome.EXPLOITED)

    def test_k8s_surface_needs_credential(self):
        """C2：6443 /version 匿名 200 + / 403 → AUTH_REQUIRED。"""
        fake = FakeTransport({
            "GET https://h:6443/version": HttpResponse(
                status=200, content_type="application/json",
                body='{"gitVersion":"v1.37.2"}'),
            "GET https://h:6443/": HttpResponse(status=403, body="forbidden"),
        })
        verdict = path_c.privesc(_ctx(transport=fake))
        self.assertIs(verdict.outcome, Outcome.AUTH_REQUIRED)
        self.assertEqual(verdict.reason, "no_credential")
        self.assertIn("kubeconfig", verdict.output)

    def test_missing_binary_is_no_tool(self):
        cmd = FakeCommand({}, default=CommandResult(code=127,
                                                   stderr="not found: id"))
        verdict = path_c.privesc(_ctx(command=cmd, exec_argv=("id",)))
        self.assertEqual(verdict.reason, "no_tool")

    def test_guardrail_block_is_blocked(self):
        cmd = FakeCommand({"id": CommandResult(code=1, stderr="RBAC: denied")})
        verdict = path_c.privesc(_ctx(command=cmd, exec_argv=("id",)))
        self.assertIs(verdict.outcome, Outcome.BLOCKED)
        self.assertEqual(verdict.reason, "guardrail")


class ImpactTests(unittest.TestCase):
    def _transport(self, bodies):
        queue = list(bodies)

        def responder(method, url, json_body):
            body = queue.pop(0)
            if isinstance(body, Exception):
                raise body
            return HttpResponse(status=200, content_type="application/json",
                                body=body)

        return FakeTransport({}, default=responder)

    def test_inference_disabled_sends_nothing(self):
        """AC-07：未开启 --allow-inference 时 impact 不得发包。"""
        fake = FakeTransport({}, default=HttpResponse(error="blocked"))
        verdict = path_c.impact(_ctx(transport=fake, allow_inference=False))
        self.assertIs(verdict.outcome, Outcome.BLOCKED)
        self.assertEqual(fake.calls, [])

    def test_stateless_success_proves_abuse_without_difference(self):
        """A2：无状态服务两次成功但结构一致 → 未授权滥用已证明（非 BLOCKED）。"""
        fake = self._transport([_body("PWNED", created="2026-11-15T00:00:01Z",
                                      duration=100),
                                _body("PWNED", created="2026-11-15T00:00:09Z",
                                      duration=999)])
        verdict = path_c.impact(_ctx(transport=fake, allow_inference=True))
        self.assertIs(verdict.outcome, Outcome.EXPOSED_NO_AUTH)
        self.assertIn("ai_log", verdict.evidence_extra)
        self.assertIn("无状态", verdict.summary)

    def test_stable_difference_proves_impact_with_ai_log(self):
        fake = self._transport([_body("BEFORE"), _body("AFTER")])
        verdict = path_c.impact(_ctx(transport=fake, allow_inference=True))
        self.assertIs(verdict.outcome, Outcome.EXPOSED_NO_AUTH)
        self.assertIn("ai_log", verdict.evidence_extra)
        self.assertIn("[before]", verdict.output)

    def test_network_failure_is_evidence_incomplete(self):
        fake = FakeTransport({}, default=HttpResponse(error="refused"))
        verdict = path_c.impact(_ctx(transport=fake, allow_inference=True))
        self.assertIs(verdict.outcome, Outcome.BLOCKED)
        self.assertEqual(verdict.reason, "evidence_incomplete")

    def test_normalisation_drops_volatile_keys(self):
        left = path_c.normalize_impact_body(_body("X", created="a", duration=1))
        right = path_c.normalize_impact_body(_body("X", created="b", duration=2))
        self.assertEqual(left, right)


class FlagTests(unittest.TestCase):
    def test_missing_channel_is_blocked(self):
        verdict = path_c.flag(_ctx(flag_panel="FLAG{a}"))
        self.assertIs(verdict.outcome, Outcome.BLOCKED)
        self.assertEqual(verdict.reason, "evidence_incomplete")

    def test_mismatch_is_blocked(self):
        verdict = path_c.flag(_ctx(flag_panel="FLAG{a}", flag_shot="FLAG{b}"))
        self.assertEqual(verdict.reason, "mismatch")

    def test_dual_channel_match_is_exploited(self):
        verdict = path_c.flag(_ctx(flag_panel="FLAG{a}", flag_shot="FLAG{a}"))
        self.assertIs(verdict.outcome, Outcome.EXPLOITED)
        self.assertEqual(verdict.evidence_extra["flag"], "FLAG{a}")


if __name__ == "__main__":
    unittest.main()


class ExecEndpointTests(unittest.TestCase):
    """SKILL.md infra-06：MODEL_SVC /exec 端点路径。"""

    def test_exec_endpoint_remote_echo_is_exploited(self):
        fake = FakeTransport({}, default=HttpResponse(
            status=200, content_type="text/plain",
            body="uid=0(root) gid=0(root) host=srv-ai-vector"))
        verdict = path_c.privesc(_ctx(transport=fake,
                                      exec_endpoint="http://h:9000/exec"))
        self.assertIs(verdict.outcome, Outcome.EXPLOITED)
        self.assertIn("/exec", verdict.command)

    def test_exec_endpoint_local_echo_is_blocked(self):
        fake = FakeTransport({}, default=HttpResponse(
            status=200, content_type="text/plain", body=socket.gethostname()))
        verdict = path_c.privesc(_ctx(transport=fake,
                                      exec_endpoint="http://h:9000/exec"))
        self.assertEqual(verdict.reason, "local_echo")

    def test_exec_endpoint_denied_is_guardrail(self):
        fake = FakeTransport({}, default=HttpResponse(status=403, body="forbidden"))
        verdict = path_c.privesc(_ctx(transport=fake,
                                      exec_endpoint="http://h:9000/exec"))
        self.assertEqual(verdict.reason, "guardrail")
