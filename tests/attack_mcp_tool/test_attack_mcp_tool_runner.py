#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""attack-mcp-tool 编排与定级测试（规格 v2 AC-01/02/08/09/10/11/17/18/19/22）。

全部离线：注入假传输、记录型证据写入器、空截图；只断言外部可观测行为。
"""
import json
import os
import re
import socket
import sys
import tempfile
import threading
import time
import unittest
import urllib.request
from unittest import mock

from tests._paths import ROOT  # noqa: E402
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from tools.pyrit_compat import TARGET_VERSION  # noqa: E402
from tools.attack_mcp_tool import (LEVELS, STEP_IDS, AttackRequest, Runtime,  # noqa: E402
                                   run_attack)
from tools.attack_mcp_tool import grade as grading  # noqa: E402
from tools.attack_mcp_tool import cli, poison  # noqa: E402
from tools.attack_mcp_tool import runner as runner_mod  # noqa: E402
from tools.attack_mcp_tool.evidence import RecordingWriter  # noqa: E402
from tools.attack_mcp_tool.model import Signals  # noqa: E402
from tools.attack_mcp_tool.shot import NullCapture  # noqa: E402
from tools.attack_mcp_tool.transport import (FakeHttpClient, HttpResponse,  # noqa: E402
                                             UrllibHttpClient)

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
        # 既有 8 步契约：mcp-01..08 必须作为前 8 个标识出现且顺序固定；
        # Ch7 增量（mcp-09/10/11）为追加，不改写既有标识（规格 #293 / 工单 #315）。
        legacy = tuple("mcp-0%d" % i for i in range(1, 9))
        self.assertEqual(STEP_IDS[:8], legacy)
        self.assertEqual(len(set(STEP_IDS)), len(STEP_IDS))  # 无重复
        for sid in legacy:
            self.assertIn(sid, STEP_IDS)

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
        self.assertEqual(graph["framework"], "pyrit==" + TARGET_VERSION)
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
        # 默认路径 A/B/C 产出既有 8 步；Ch7 新步骤（mcp-09..11）须显式选 D/E/F 才执行。
        self.assertEqual([v.step_id for v in report.verdicts],
                         list("mcp-0%d" % i for i in range(1, 9)))


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
               "shutil", "posixpath"}

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


class JsonRpcFullEmitTests(unittest.TestCase):
    """D-1 回归：jsonrpc 形态全路径必须完整落盘 11 份证据。

    修复前 `_render()` 仅在 `text` 与 `raw` 同时非空时输出文本，mcp-06/mcp-08
    的纯文本降级说明不被计为「关键输出」，严格证据门抛 RuntimeError 中断整轮，
    导致 mcp-07..11 与 flag 步不执行、片段仅落盘 6 份。
    """

    @staticmethod
    def _section_body(text, heading):
        marker = "#### " + heading
        start = text.find(marker)
        if start < 0:
            return ""
        body = text[start + len(marker):]
        nxt = body.find("\n#### ")
        return body if nxt < 0 else body[:nxt]

    def test_jsonrpc_full_path_emits_all_eleven_steps(self):
        server = poison.PoisonedMcpServer().start()
        try:
            with tempfile.TemporaryDirectory() as tmp:
                report = run_attack(
                    AttackRequest(target=server.url, mode="jsonrpc", labs=(),
                                  paths=("A", "B", "C", "D", "E", "F"),
                                  evidence_dir=tmp, emit=True),
                    Runtime(client=UrllibHttpClient(), capture=NullCapture()))
                self.assertEqual(len(report.verdicts), 11)
                self.assertEqual({v.step_id for v in report.verdicts}, set(STEP_IDS))
                for verdict in report.verdicts:
                    with self.subTest(step=verdict.step_id):
                        self.assertTrue(verdict.evidence_path,
                                        "%s 未落盘证据" % verdict.step_id)
                        self.assertTrue(os.path.exists(verdict.evidence_path))
                        with open(verdict.evidence_path, encoding="utf-8") as f:
                            text = f.read()
                        self.assertIn("#### 关键输出", text)
                        self.assertTrue(
                            self._section_body(text, "关键输出").strip(),
                            "证据片段「关键输出」为空：%s" % verdict.step_id)
                levels = {v.step_id: v.level for v in report.verdicts}
                self.assertEqual(levels["mcp-06"], "已跳过")
                self.assertEqual(levels["mcp-08"], "已跳过")
        finally:
            server.stop()


class ServerOwnershipTests(unittest.TestCase):
    """AC-04 / AC-05 / AC-06：谁启动谁关闭。"""

    def _run_mcp02(self, runtime):
        return run_attack(AttackRequest(target="http://127.0.0.1:1/mcp", mode="jsonrpc",
                                        step="mcp-02"), runtime)

    def test_injected_running_server_is_neither_started_nor_stopped(self):
        server = poison.PoisonedMcpServer().start()
        self.addCleanup(server.stop)
        port = server.port
        runtime = Runtime(client=FakeHttpClient({}), writer=RecordingWriter(),
                          capture=NullCapture(), server=server)
        run_attack(AttackRequest(target="http://127.0.0.1:1/mcp", mode="jsonrpc",
                                 paths=("A", "B", "C", "D", "E", "F"), emit=False), runtime)
        self.assertTrue(server.is_running, "编排层不得关闭注入方持有的实例")
        with urllib.request.urlopen("http://127.0.0.1:%d/tools/list" % port,
                                    timeout=5) as resp:
            self.assertEqual(resp.status, 200)

    def test_injected_idle_server_is_started_and_stopped_by_runner(self):
        server = poison.PoisonedMcpServer()
        runtime = Runtime(client=FakeHttpClient({}), writer=RecordingWriter(),
                          capture=NullCapture(), server=server)
        self._run_mcp02(runtime)
        self.assertFalse(server.is_running, "编排层启动的实例应由其关闭")
        _assert_port_released(self, server.port)

    def test_self_created_server_is_started_and_stopped(self):
        """AC-06：未注入时编排层自建、自启动、自关闭。"""
        made = []
        real_server = poison.PoisonedMcpServer   # 先取真实类，避免 patch 后自递归

        def factory():
            server = real_server()
            made.append(server)
            return server

        runtime = Runtime(client=FakeHttpClient({}), writer=RecordingWriter(),
                          capture=NullCapture())
        with mock.patch.object(runner_mod.poison, "PoisonedMcpServer",
                               mock.MagicMock(side_effect=factory)):
            self._run_mcp02(runtime)
        self.assertEqual(len(made), 1, "未注入时应恰好自建一个 server")
        self.assertFalse(made[0].is_running, "自建实例须由编排层关闭")
        _assert_port_released(self, made[0].port)

    def test_real_port_conflict_degrades_mcp02_to_skipped(self):
        """AC-07：真实占用端口（非 stub）时 mcp-02 判已跳过且理由含端口。"""
        holder = poison.PoisonedMcpServer().start()
        self.addCleanup(holder.stop)
        contender = poison.PoisonedMcpServer(port=holder.port)
        runtime = Runtime(client=FakeHttpClient({}), writer=RecordingWriter(),
                          capture=NullCapture(), server=contender)
        report = run_attack(AttackRequest(target="http://127.0.0.1:1/mcp", mode="jsonrpc",
                                          paths=("A",), emit=False), runtime)
        by_id = {v.step_id: v for v in report.verdicts}
        self.assertEqual(by_id["mcp-02"].level, "已跳过")
        self.assertIn("端口", by_id["mcp-02"].reason)
        self.assertTrue(holder.is_running, "冲突不得影响端口既有持有者")
        # 启动失败后不得被后续步骤当作就绪实例复用（端口仍为占位 0）
        for sid in ("mcp-03", "mcp-04"):
            self.assertNotIn(":0/mcp", by_id[sid].command,
                             "%s 复用了启动失败的实例" % sid)

    def test_self_created_server_leaves_no_listener_thread(self):
        runtime = Runtime(client=FakeHttpClient({}), writer=RecordingWriter(),
                          capture=NullCapture())
        self._run_mcp02(runtime)
        alive = [t for t in threading.enumerate() if t.name == "malicious-mcp"]
        self.assertEqual(alive, [], "未注入时编排层自建的监听线程必须被关闭")


def _assert_port_released(case, port, window=2.0):
    """AC-05：关闭后在退避窗口内可重绑（不承诺立即）。"""
    deadline = time.time() + window
    while True:
        probe = socket.socket()
        try:
            probe.bind(("127.0.0.1", port))
            return
        except OSError:
            if time.time() > deadline:
                case.fail("端口 %d 未在 %.1fs 内释放" % (port, window))
            time.sleep(0.05)
        finally:
            probe.close()


class RunnerBranchTests(unittest.TestCase):
    """注入点覆盖、降级路径与异常收敛（补齐 D-3 覆盖洼地）。"""

    def test_runtime_builds_default_capture_when_not_injected(self):
        self.assertIsNotNone(Runtime(client=FakeHttpClient({})).capture)

    def test_curl_without_body_renders_get_form(self):
        self.assertEqual(runner_mod._curl("GET", "http://t.example/x"),
                         "curl -sN -X GET 'http://t.example/x'")

    def test_paths_argument_overrides_request_paths(self):
        report = run_attack(AttackRequest(target="http://t.example", mode="jsonrpc"),
                            offline({}), paths=("A",))
        self.assertEqual([v.step_id for v in report.verdicts],
                         ["mcp-01", "mcp-02", "mcp-03", "mcp-04", "mcp-08"])

    def test_prompt_for_override_replaces_step_prompt(self):
        client = FakeHttpClient({("POST", "http://t.example/api/labs/MCP_01/chat"):
                                 HttpResponse(status=200,
                                              body=sse(["- **Tool name:** `get_config`"]))})
        seen = []
        runtime = Runtime(client=client, writer=RecordingWriter(), capture=NullCapture(),
                          prompt_for=lambda spec: seen.append(spec.step_id) or "CUSTOM-PROMPT")
        run_attack(AttackRequest(target="http://t.example", step="mcp-01"), runtime)
        self.assertEqual(seen, ["mcp-01"])
        self.assertEqual(client.calls[0]["json_body"]["prompt"], "CUSTOM-PROMPT")

    def test_step_exception_is_contained_and_not_marked_skipped(self):
        class ExplodingClient:
            def describe(self):
                return "exploding"

            def request(self, *args, **kwargs):
                raise KeyError("boom")

        runtime = Runtime(client=ExplodingClient(), writer=RecordingWriter(),
                          capture=NullCapture())
        report = run_attack(AttackRequest(target="http://t.example", step="mcp-01"), runtime)
        verdict = report.verdicts[0]
        # 执行异常 != 目标能力缺失：不得记为「已跳过」，须如实标为未生效
        self.assertEqual(verdict.level, "未生效")
        self.assertIn("执行异常", verdict.reason)

    def test_evidence_gate_failure_propagates_as_runtime_error(self):
        class FailingWriter:
            def describe(self):
                return "failing"

            def fragment_path(self, step_id):
                return "<memory>/%s.md" % step_id

            def emit(self, **kwargs):
                return self.fragment_path(kwargs.get("step_id", "")), 1, "模拟门禁失败"

        runtime = Runtime(client=FakeHttpClient({}), writer=FailingWriter(),
                          capture=NullCapture())
        with self.assertRaises(RuntimeError):
            run_attack(AttackRequest(target="http://t.example", step="mcp-04", emit=True),
                       runtime)

    def test_jsonrpc_tools_list_error_marks_capability_missing(self):
        runtime = offline({("POST", "http://t.example/mcp"):
                           HttpResponse(status=500, body="boom")})
        report = run_attack(AttackRequest(target="http://t.example/mcp", mode="jsonrpc",
                                          step="mcp-01"), runtime)
        verdict = report.verdicts[0]
        self.assertEqual(verdict.level, "已跳过")
        self.assertIn("tools/list", verdict.reason)

    def test_local_port_unavailable_degrades_to_skipped(self):
        class BusyServer(poison.PoisonedMcpServer):
            def start(self):
                raise OSError("port in use")

        runtime = Runtime(client=FakeHttpClient({}), writer=RecordingWriter(),
                          capture=NullCapture(), server=BusyServer())
        report = run_attack(AttackRequest(target="http://t.example", mode="jsonrpc",
                                          step="mcp-02"), runtime)
        verdict = report.verdicts[0]
        self.assertEqual(verdict.level, "已跳过")
        self.assertIn("端口", verdict.reason)

    def test_jsonrpc_admin_tool_is_resolved_from_surface(self):
        tools_body = {"jsonrpc": "2.0", "id": 1, "result": {"tools": [
            {"name": "admin_action", "description": "Administrative action",
             "_scope": "admin", "_server_id": "attacker_mcp", "_trust": "untrusted"}]}}

        def router(body):
            if isinstance(body, dict) and body.get("method") == "tools/call":
                return HttpResponse(status=200, body=json.dumps({
                    "jsonrpc": "2.0", "id": body.get("id"),
                    "result": {"content": [{"type": "text", "text": '{"admin": true}'}],
                               "isError": False}}))
            return HttpResponse(status=200, body=json.dumps(tools_body))

        runtime = Runtime(client=FakeHttpClient({("POST", "http://t.example/mcp"): router}),
                          writer=RecordingWriter(), capture=NullCapture())
        report = run_attack(AttackRequest(target="http://t.example/mcp", mode="jsonrpc",
                                          step="mcp-07"), runtime)
        verdict = report.verdicts[0]
        self.assertIn("admin_action", verdict.command,
                      "应按目标实际工具面解析 admin 角色，而非契约默认名")
        self.assertEqual(verdict.level, "完全生效")


if __name__ == "__main__":
    unittest.main()
