#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""attack-multi-agent 示意脚本测试（SKILL.md 点名的 5 个顶层薄壳）。

断言：SKILL.md 列出的命令字面可执行（--dry-run 渲染同源命令）、
成功/不可达退出码正确、JSON 输出结构稳定、`--before` 形成前后对照。
薄壳不重复实现逻辑，故此处只验「参数 → a2a.py 调用 → 输出」的接线。
"""
import contextlib
import io
import json
import unittest

import tools.agent_impersonate as agent_impersonate
import tools.context_poison as context_poison
import tools.memory_poison as memory_poison
import tools.msg_inject as msg_inject
import tools.workflow_disrupt as workflow_disrupt
from tools.attack_multi_agent import poc
from tools.attack_multi_agent.transport import DryRunClient, FakeHttpClient, Response


def out_of(func, argv):
    """运行脚本 main，返回 (退出码, stdout)。"""
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        code = func(argv)
    return code, buf.getvalue()


class DryRunTests(unittest.TestCase):
    """--dry-run 不发请求，但必须渲染与真实执行同源的 curl 命令。"""

    def test_build_client_switch(self):
        self.assertIsInstance(poc.build_client(True), DryRunClient)
        self.assertEqual(poc.build_client(True).describe(), "dry-run")

    def test_msg_inject_dry_run(self):
        code, out = out_of(msg_inject.main, [
            "--bus", "http://b", "--from", "agentA", "--to", "agentB",
            "--payload", "p", "--dry-run"])
        self.assertEqual(code, 0)
        self.assertIn("/publish", out)
        self.assertIn("dry-run", out)

    def test_agent_impersonate_dry_run(self):
        code, out = out_of(agent_impersonate.main, [
            "--bus", "http://b", "--spoof", "agentA", "--cmd", "c", "--dry-run"])
        self.assertEqual(code, 0)
        self.assertIn("/agent/agentA/cmd", out)

    def test_memory_poison_dry_run(self):
        code, out = out_of(memory_poison.main, [
            "--store", "http://m", "--value", "v", "--dry-run"])
        self.assertEqual(code, 0)
        self.assertIn("/set", out)

    def test_context_poison_dry_run(self):
        code, out = out_of(context_poison.main, [
            "--endpoint", "http://o/context", "--inject", "i", "--dry-run"])
        self.assertEqual(code, 0)
        self.assertIn("http://o/context", out)

    def test_workflow_disrupt_dry_run(self):
        code, out = out_of(workflow_disrupt.main, [
            "--orchestrator", "http://o", "--task", "t", "--dry-run"])
        self.assertEqual(code, 0)
        self.assertIn("/task", out)

    def test_json_output(self):
        code, out = out_of(msg_inject.main, [
            "--bus", "http://b", "--from", "a", "--to", "b",
            "--payload", "p", "--dry-run", "--json"])
        self.assertEqual(code, 0)
        data = json.loads(out)
        self.assertTrue(data["dry_run"])
        self.assertIn("/publish", data["step_command"])


class LivePathTests(unittest.TestCase):
    """注入替身验证真实执行分支与退出码（不触网）。"""

    def setUp(self):
        self._saved = poc.build_client

    def tearDown(self):
        poc.build_client = self._saved

    def _patch(self, client):
        poc.build_client = lambda dry_run=False: client

    def test_success_exit_zero(self):
        self._patch(FakeHttpClient(default=Response(200, "accepted", "application/json")))
        code, out = out_of(msg_inject.main, [
            "--bus", "http://b", "--from", "a", "--to", "b", "--payload", "p"])
        self.assertEqual(code, 0)
        self.assertIn("accepted", out)

    def test_unreachable_exit_three(self):
        self._patch(FakeHttpClient(default=Response(0, "", "", error="boom")))
        code, out = out_of(workflow_disrupt.main, [
            "--orchestrator", "http://o", "--task", "t"])
        self.assertEqual(code, 3)
        self.assertIn("boom", out)

    def test_memory_poison_before_pair(self):
        client = FakeHttpClient(script={"http://m/get": Response(200, "old-memory", "text/plain")},
                                default=Response(200, "ok", "application/json"))
        self._patch(client)
        code, out = out_of(memory_poison.main, [
            "--store", "http://m", "--key", "conv:agentB", "--value", "new", "--before"])
        self.assertEqual(code, 0)
        self.assertIn("投毒前", out)
        self.assertIn("old-memory", out)

    def test_poc_run_direct(self):
        from tools.attack_multi_agent.model import Observation
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            first = poc.run(Observation(text="x"), "cmd", dry_run=True)
            second = poc.run(Observation(error="e"), "cmd")
        self.assertEqual(first, poc.EXIT_OK)
        self.assertEqual(second, poc.EXIT_UNREACHABLE)


if __name__ == "__main__":
    unittest.main()
