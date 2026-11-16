#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""路径 B 测试（infra-04..05）：容器授权面 / 网关凭据指纹。

对齐 AC-05/09/10/11。
"""
import os
import shutil
import sys
import tempfile
import unittest

from tests._paths import ROOT  # noqa: E402
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from tools.attack_infra import path_b  # noqa: E402
from tools.attack_infra.command import CommandResult, FakeCommand  # noqa: E402
from tools.attack_infra.model import Outcome, RunContext  # noqa: E402
from tools.attack_infra.transport import FakeTransport  # noqa: E402

SECRET = "sk-testFAKE1234567890abcdefGHIJ"


def _ctx(command, **kwargs):
    base = dict(target="h", transport=FakeTransport({}), command=command,
                timeout=5)
    base.update(kwargs)
    return RunContext(**base)


class ContainerTests(unittest.TestCase):
    def test_high_privilege_surface_is_exposed(self):
        cmd = FakeCommand({"kubectl": CommandResult(
            code=0, stdout="Resources  Non-Resource URLs\n*.*        []\n")})
        verdict = path_b.container(_ctx(cmd))
        self.assertIs(verdict.outcome, Outcome.EXPOSED_NO_AUTH)
        self.assertIn("高权项", verdict.summary)

    def test_low_privilege_surface_is_absent(self):
        cmd = FakeCommand({"kubectl": CommandResult(
            code=0, stdout="pods  []  [get]\n")})
        verdict = path_b.container(_ctx(cmd))
        self.assertIs(verdict.outcome, Outcome.ABSENT)
        self.assertEqual(verdict.reason, "none_found")

    def test_forbidden_is_auth_required(self):
        cmd = FakeCommand({"kubectl": CommandResult(
            code=1, stderr="error: You must be logged in to the server (Unauthorized)")})
        verdict = path_b.container(_ctx(cmd))
        self.assertIs(verdict.outcome, Outcome.AUTH_REQUIRED)
        self.assertEqual(verdict.reason, "forbidden")

    def test_missing_kubectl_is_no_tool(self):
        cmd = FakeCommand({}, default=CommandResult(code=127,
                                                   stderr="not found: kubectl"))
        verdict = path_b.container(_ctx(cmd))
        self.assertEqual(verdict.reason, "no_tool")

    def test_service_account_impersonation_is_parameterised(self):
        """AC-10：命令以参数列表传入，服务账号以 --as= 形式出现。"""
        cmd = FakeCommand({"kubectl": CommandResult(code=0, stdout="")})
        path_b.container(_ctx(cmd, namespace="prod", service_account="sa1"))
        argv = cmd.calls[0]
        self.assertEqual(argv[0], "kubectl")
        self.assertIn("--as=system:serviceaccount:prod:sa1", argv)
        self.assertIn("-n", argv)


class GatewayTests(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp(prefix="attack-infra-")

    def tearDown(self):
        shutil.rmtree(self.dir, ignore_errors=True)

    def _write(self, name, text):
        path = os.path.join(self.dir, name)
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(text)
        return path

    def test_no_config_is_absent(self):
        verdict = path_b.gateway(_ctx(FakeCommand({})))
        self.assertIs(verdict.outcome, Outcome.ABSENT)
        self.assertEqual(verdict.reason, "none_found")

    def test_credential_hint_without_plaintext(self):
        """AC-09：只出指纹，明文不得出现在输出中。"""
        path = self._write("config.yaml",
                           "model_list:\n  - api_key: %s\n" % SECRET)
        verdict = path_b.gateway(_ctx(FakeCommand({}), gateway_configs=(path,)))
        self.assertIs(verdict.outcome, Outcome.EXPOSED_NO_AUTH)
        self.assertIn("sk-…(len=", verdict.output)
        self.assertNotIn(SECRET, verdict.output)
        self.assertNotIn(SECRET, verdict.command)

    def test_bearer_and_akia_patterns(self):
        path = self._write("env.txt",
                           "AWS_ACCESS_KEY_ID=AKIAEXAMPLE123456789\n"
                           "Authorization: Bearer abcdef1234567890\n")
        verdict = path_b.gateway(_ctx(FakeCommand({}), gateway_configs=(path,)))
        self.assertIn("AKIA", verdict.output)
        self.assertIn("Bearer", verdict.output)

    def test_duplicate_hints_are_deduplicated(self):
        path = self._write("dup.yaml", "a: %s\nb: %s\n" % (SECRET, SECRET))
        verdict = path_b.gateway(_ctx(FakeCommand({}), gateway_configs=(path,)))
        self.assertIn("检出 1 条凭据指纹", verdict.summary)

    def test_missing_file_is_tolerated(self):
        verdict = path_b.gateway(_ctx(FakeCommand({}),
                                      gateway_configs=(os.path.join(self.dir, "nope"),)))
        self.assertIs(verdict.outcome, Outcome.ABSENT)


if __name__ == "__main__":
    unittest.main()


class GatewayLegalIdentityTests(unittest.TestCase):
    """SKILL.md infra-05：以合法身份调用推理；凭据明文不得入片段。"""

    SECRET = "sk-LEGALIDENTITY1234567890abcdef"

    def test_credential_driven_inference_is_exploited_without_plaintext(self):
        import tempfile
        import shutil
        from tools.attack_infra.transport import HttpResponse
        tmp = tempfile.mkdtemp(prefix="attack-infra-gw-")
        cfg = os.path.join(tmp, "config.yaml")
        with open(cfg, "w", encoding="utf-8") as handle:
            handle.write("api_key: %s\n" % self.SECRET)
        body = '{"choices":[{"text":"OK"}]}' 
        fake = FakeTransport({}, default=HttpResponse(
            status=200, content_type="application/json", body=body))
        ctx = RunContext(
            target="h", transport=fake, command=FakeCommand({}), timeout=5,
            gateway_configs=(cfg,), gateway_credential=self.SECRET,
            gateway_verify_endpoint="http://h:4000/chat/completions",
            allow_inference=True)
        verdict = path_b.gateway(ctx)
        self.assertIs(verdict.outcome, Outcome.EXPLOITED)
        self.assertIn("$GATEWAY_TOKEN", verdict.command)
        self.assertNotIn(self.SECRET, verdict.command)
        self.assertNotIn(self.SECRET, verdict.output)
        self.assertEqual(fake.requests[0][2].get("Authorization"),
                         "Bearer %s" % self.SECRET)
        shutil.rmtree(tmp, ignore_errors=True)

    def test_no_inference_switch_means_no_call(self):
        fake = FakeTransport({})
        ctx = RunContext(
            target="h", transport=fake, command=FakeCommand({}), timeout=5,
            gateway_configs=("config.yaml",), gateway_credential=self.SECRET,
            gateway_verify_endpoint="http://h:4000/chat/completions")
        path_b.gateway(ctx)
        self.assertEqual(fake.calls, [])
