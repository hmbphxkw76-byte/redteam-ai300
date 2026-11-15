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

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
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
