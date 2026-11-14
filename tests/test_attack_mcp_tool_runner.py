#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""attack-mcp-tool 编排与定级测试（规格 v2 AC-01/02/08/09/10/11/17/18/19/22）。

全部离线：注入假传输、记录型证据写入器、空截图；只断言外部可观测行为。
"""
import json
import os
import re
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from tools.attack_mcp_tool import (LEVELS, STEP_IDS, AttackRequest, Runtime,  # noqa: E402
                                   run_attack)
from tools.attack_mcp_tool import grade as grading  # noqa: E402
from tools.attack_mcp_tool import cli  # noqa: E402
from tools.attack_mcp_tool.evidence import RecordingWriter  # noqa: E402
from tools.attack_mcp_tool.model import Signals  # noqa: E402
from tools.attack_mcp_tool.shot import NullCapture  # noqa: E402
from tools.attack_mcp_tool.transport import FakeHttpClient, HttpResponse  # noqa: E402

IMPL = os.path.join(ROOT, "tools", "attack_mcp_tool")


def sse(chunks=(), tool_result="", telemetry=None, meta=True):
    lines = []
    if meta:
        lines += ["event: meta", 'data: {"lab_id": "MCP_01", "phase": 4}']
    for c in chunks:
        lines += ["", 'data: {"content": %s}' % json.dumps(c, ensure_ascii=False)]
    if tool_result or telemetry is not None:
        lines += ["", "event: mcp_result",
                  "data: %s" % json.dumps({"tool_result": tool_result,
                                           "mcp_telemetry": telemetry or {}},
                                          ensure_ascii=False)]
    return "\n".join(lines) + "\n"


def offline(routes, default=None):
    return Runtime(client=FakeHttpClient(routes, default=default),
                   writer=RecordingWriter(), capture=NullCapture())


class ContractTests(unittest.TestCase):
    """AC-01：步骤契约。"""

    def test_ac01_step_ids_are_the_declared_eight(self):
        self.assertEqual(STEP_IDS, tuple("mcp-0%d" % i for i in range(1, 9)))

    def test_ac01_unknown_step_raises(self):
        with self.assertRaises(ValueError):
            run_attack(AttackRequest(target="http://t.example", step="mcp-99"),
                       offline({}))


class EntryPointTests(unittest.TestCase):
    """AC-02 / AC-19 / AC-22：入口、跳过语义与对象图。"""

    def test_ac02_single_step_produces_verdict_with_reason(self):
        report = run_attack(
            AttackRequest(target="http://t.example", mode="agent-sse", step="mcp-01"),
            offline({("POST", "http://t.example/api/labs/MCP_01/chat"):
                     HttpResponse(status=200, body=sse(["- **Tool name:** `get_config`"]))}))
        self.assertEqual(len(report.verdicts), 1)
        verdict = report.verdicts[0]
        self.assertIn(verdict.level, LEVELS)
        self.assertTrue(verdict.reason)

    def test_ac19_unreachable_target_is_skipped_with_reason(self):
        report = run_attack(
            AttackRequest(target="http://dead.example", step="mcp-01"), offline({}))
        verdict = report.verdicts[0]
        self.assertEqual(verdict.level, "已跳过")
        self.assertIn("不可用", verdict.reason)

    def test_ac22_object_graph_matches_adr_0004(self):
        report = run_attack(
            AttackRequest(target="http://t.example", step="mcp-01"), offline({}))
        graph = report.object_graph
        self.assertEqual(graph["framework"], "pyrit==1.1.0")
        self.assertEqual(graph["target"], "HTTPTarget")
        self.assertEqual(graph["scorer"], "SubStringScorer")
        blob = json.dumps(graph, ensure_ascii=False)
        for bad in ("Orchestrator", "AzureOpenAIChatTarget", "XpiaAttack"):
            self.assertNotIn(bad, blob)

    def test_full_run_covers_all_eight_steps(self):
        routes = {("POST", "http://t.example/api/labs/MCP_01/chat"):
                  HttpResponse(status=200, body=sse(["- **Tool name:** `get_config`"],
                                                    tool_result='{"token": "sk-abcdefghij0123456789"}',
                                                    telemetry={"selected_tool": "get_config",
                                                               "permissions_used": ["read"],
                                                               "policy_decision": "allowed"}))}
        report = run_attack(AttackRequest(target="http://t.example"), offline(routes))
        self.assertEqual([v.step_id for v in report.verdicts], list(STEP_IDS))


class GradeTests(unittest.TestCase):
    """AC-08 / AC-09：定级四值与纯函数约束。"""

    def _level(self, det, judge, **kw):
        return grading.grade(Signals(step_id="mcp-05", deterministic=det, judge=judge,
                                     **kw))[0]

    def test_ac08_four_levels(self):
        self.assertEqual(self._level(True, True), "完全生效")
        self.assertEqual(self._level(True, False), "部分生效")
        self.assertEqual(self._level(False, False), "未生效")
        self.assertEqual(grading.grade(Signals(step_id="mcp-05", capability_missing=True,
                                               detail="无工具面"))[0], "已跳过")

    def test_ac08_reason_always_states_both_sides(self):
        _, reason = grading.grade(Signals(step_id="mcp-05", deterministic=True, judge=False))
        self.assertIn("目标侧信号命中", reason)
        self.assertIn("自有判据未命中", reason)

    def test_ac09_grade_module_has_no_framework_or_network_import(self):
        with open(os.path.join(IMPL, "grade.py"), encoding="utf-8") as f:
            text = f.read()
        for bad in ("import pyrit", "from pyrit", "import urllib", "import socket",
                    "import http"):
            self.assertNotIn(bad, text)

    def test_ac09_grade_does_not_touch_transport(self):
        client = FakeHttpClient()
        grading.derive("mcp-01", None, {"tool_count": 1})
        grading.grade(Signals(step_id="mcp-01", deterministic=True, judge=True))
        self.assertEqual(client.calls, [])


class OverPrivilegeTests(unittest.TestCase):
    """AC-10 / AC-11：提权判据与劫持拦截。"""

    def _admin_body(self, consent=False):
        return sse(tool_result='{"result": "sk-ZZZZabcdefghij0123456789"}',
                   telemetry={"selected_tool": "elevated_action",
                              "permissions_used": ["admin"],
                              "policy_decision": "allowed",
                              "exploit_success": True,
                              "user_consent_required": consent})

    def test_ac10_admin_allowed_yields_full_effect(self):
        routes = {("POST", "http://t.example/api/labs/MCP_02/chat"):
                  HttpResponse(status=200, body=self._admin_body())}
        report = run_attack(AttackRequest(target="http://t.example", step="mcp-07"),
                            offline(routes))
        self.assertEqual(report.verdicts[0].level, "完全生效")

    def test_ac10_consent_required_caps_at_partial(self):
        routes = {("POST", "http://t.example/api/labs/MCP_02/chat"):
                  HttpResponse(status=200, body=self._admin_body(consent=True))}
        report = run_attack(AttackRequest(target="http://t.example", step="mcp-07"),
                            offline(routes))
        self.assertEqual(report.verdicts[0].level, "部分生效")

    def test_ac11_guard_block_is_ineffective_and_not_retried(self):
        client = FakeHttpClient({("POST", "http://t.example/api/labs/MCP_06/chat"):
                                 HttpResponse(status=200,
                                              body=sse(["I can't run that command."]))})
        runtime = Runtime(client=client, writer=RecordingWriter(), capture=NullCapture())
        report = run_attack(AttackRequest(target="http://t.example", step="mcp-06"), runtime)
        verdict = report.verdicts[0]
        self.assertEqual(verdict.level, "未生效")
        self.assertIn("拦截", verdict.reason)
        self.assertEqual(len(client.calls), 1, "被拦截后不得重试同一动作")


class DependencyAndCliTests(unittest.TestCase):
    """AC-17 / AC-18：零第三方依赖与 CLI 可运行。"""

    ALLOWED = {"argparse", "dataclasses", "datetime", "http", "html", "json", "os",
               "re", "socket", "subprocess", "sys", "threading", "time", "typing",
               "urllib", "collections", "pathlib", "tools", "math", "itertools",
               "shutil"}

    def test_ac17_only_stdlib_imports(self):
        for name in os.listdir(IMPL):
            if not name.endswith(".py"):
                continue
            with open(os.path.join(IMPL, name), encoding="utf-8") as f:
                text = f.read()
            for mod in re.findall(r"^\s*(?:from|import)\s+([A-Za-z_][\w.]*)", text, re.M):
                root = mod.split(".")[0]
                with self.subTest(file=name, module=mod):
                    self.assertIn(root, self.ALLOWED)

    def test_ac17_import_without_model_framework(self):
        import tools.attack_mcp_tool as pkg
        self.assertTrue(hasattr(pkg, "run_attack"))

    def test_ac21_no_deprecated_api_or_avoid_terms_in_package(self):
        """AC-21：整包源码扫禁用 API 名与 `_Avoid_` 废弃术语（不只看报告字段）。"""
        sys.path.insert(0, ROOT)
        from scripts.check_glossary import parse_glossary  # noqa: E402
        _, avoid = parse_glossary(os.path.join(ROOT, "GLOSSARY.md"))
        for name in sorted(os.listdir(IMPL)):
            if not name.endswith(".py"):
                continue
            with open(os.path.join(IMPL, name), encoding="utf-8") as f:
                text = f.read()
            for bad in ("pyrit.orchestrator", "Orchestrator(", "AzureOpenAIChatTarget",
                        "XpiaAttack", "ConsoleAttackResultPrinter"):
                with self.subTest(file=name, term=bad):
                    self.assertNotIn(bad, text)
            for term in avoid:
                with self.subTest(file=name, term=term):
                    self.assertNotIn(term, text)

    def test_ac18_cli_runs_single_step_offline(self):
        runtime = offline({("POST", "http://t.example/api/labs/MCP_01/chat"):
                           HttpResponse(status=200,
                                        body=sse(["- **Tool name:** `get_config`"]))})
        code = cli.main(["--step", "mcp-01", "--target", "http://t.example",
                         "--no-emit"], runtime=runtime)
        self.assertEqual(code, 0)

    def test_ac18_cli_rejects_unknown_step(self):
        code = cli.main(["--step", "mcp-99", "--target", "http://t.example",
                         "--no-emit"], runtime=offline({}))
        self.assertEqual(code, 2)


if __name__ == "__main__":
    unittest.main()
