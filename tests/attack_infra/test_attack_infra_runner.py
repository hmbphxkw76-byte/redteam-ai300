#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""编排与 CLI 测试：诱饵早停 / 证据门 / 报告 / 退出码。

对齐 AC-13/15/16/17/18/19。
"""
import json
import os
import socket
import sys
import unittest

from tests._paths import ROOT  # noqa: E402
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from tools.attack_infra import cli, report, runner  # noqa: E402
from tools.attack_infra.command import CommandResult, FakeCommand  # noqa: E402
from tools.attack_infra.evidence import FakeEvidence  # noqa: E402
from tools.attack_infra import model  # noqa: E402
from tools.attack_infra.model import (  # noqa: E402
    STEP_IDS, Outcome, RunContext,
)
from tools.attack_infra.shot import ShotPlanner  # noqa: E402
from tools.attack_infra.transport import FakeTransport, HttpResponse  # noqa: E402

SPA = HttpResponse(status=200, content_type="text/html", body="<html></html>")
OLLAMA = HttpResponse(status=200, content_type="application/json",
                      body=json.dumps({"models": [{"name": "llama3.2:latest"}]}))
GENERATE = HttpResponse(status=200, content_type="application/json",
                        body=json.dumps({"response": "PWNED", "done": True}))


def _full_ctx(**kwargs):
    routes = {
        "GET http://h:11434/api/tags": OLLAMA,
        "POST http://h:11434/api/generate": GENERATE,
    }
    base = dict(target="h", transport=FakeTransport(routes, default=SPA),
                command=FakeCommand({}, default=CommandResult(code=127,
                                                             stderr="not found")),
                evidence=FakeEvidence(), shot=ShotPlanner("loot/shots"),
                timeout=5, ports=(11434,), step_ids=STEP_IDS,
                inference_endpoint="http://h:11434/api/generate",
                allow_inference=True, flag_panel="FLAG{a}", flag_shot="FLAG{a}")
    base.update(kwargs)
    return RunContext(**base)


class RunnerTests(unittest.TestCase):
    def test_decoy_sends_zero_requests(self):
        """AC-17：诱饵机判据命中后不得再发包。"""
        ctx = _full_ctx(decoy=True)
        result = runner.run(ctx)
        self.assertEqual(ctx.transport.calls, [])
        self.assertEqual(result.steps, [])
        self.assertIn("诱饵机", result.notes[0])

    def test_all_eight_steps_execute(self):
        ctx = _full_ctx()
        result = runner.run(ctx)
        self.assertEqual([s.step_id for s in result.steps], list(STEP_IDS))

    def test_every_step_emits_evidence(self):
        ctx = _full_ctx()
        runner.run(ctx)
        recorded = {r["step_id"] for r in ctx.evidence.records}
        self.assertEqual(recorded, set(STEP_IDS))

    def test_evidence_failure_marks_blocking(self):
        """B4 / AC-15：证据门失败视为阻断项，但不改变判定。"""
        ctx = _full_ctx(evidence=FakeEvidence(exit_code=1, error="missing shot"))
        result = runner.run(ctx)
        self.assertTrue(any(not s.evidence_ok for s in result.steps))
        self.assertTrue(result.blocking())
        self.assertEqual(report.exit_code(result), 1)

    def test_unknown_step_raises(self):
        with self.assertRaises(ValueError):
            runner.run(_full_ctx(step_ids=("infra-01", "infra-77")))

    def test_absent_steps_produce_handoff_suggestion(self):
        ctx = _full_ctx(transport=FakeTransport({}, default=SPA),
                        ports=(11434,), allow_inference=False)
        result = runner.run(ctx)
        self.assertTrue(result.next_skills())
        self.assertIn("attack-mcp-tool", report.render(result))

    def test_report_commands_have_no_angle_bracket_placeholders(self):
        ctx = _full_ctx()
        result = runner.run(ctx)
        for step in result.steps:
            self.assertNotIn("<", step.command,
                             "%s 命令含占位符：%s" % (step.step_id, step.command))


class PostureTests(unittest.TestCase):
    """AC-08 / AC-13 / AC-19：只读姿态、AI 日志、离线可测。"""

    BLACKLIST = ("pull", "delete", "create", "unload", "update_weights")

    def test_default_run_never_writes_or_touches_write_paths(self):
        ctx = _full_ctx(allow_inference=False)
        runner.run(ctx)
        methods = set(ctx.transport.methods())
        self.assertEqual(methods - {"GET"}, set(),
                         "默认运行出现写方法：%s" % (methods - {"GET"},))
        for path in ctx.transport.called_paths():
            for token in self.BLACKLIST:
                self.assertNotIn(token, path, "访问了写路径：%s" % path)

    def test_impact_records_ai_log_when_proven(self):
        bodies = [json.dumps({"response": "BEFORE", "done": True}),
                  json.dumps({"response": "AFTER", "done": True})]

        def responder(method, url, json_body):
            return HttpResponse(status=200, content_type="application/json",
                                body=bodies.pop(0) if bodies else "{}")

        ctx = _full_ctx(transport=FakeTransport({}, default=responder),
                        allow_inference=True, step_ids=("infra-07",))
        result = runner.run(ctx)
        verdict = [s for s in result.steps if s.step_id == "infra-07"][0]
        self.assertIn("ai_log", verdict.evidence_extra)
        record = [r for r in ctx.evidence.records if r["step_id"] == "infra-07"][0]
        self.assertTrue(record.get("ai_log"))

    def test_suite_path_opens_no_external_socket(self):
        real_connect = socket.socket.connect

        def guard(self, address):
            host = address[0] if isinstance(address, tuple) else str(address)
            if not (str(host).startswith("127.") or host in ("::1", "localhost")):
                raise AssertionError("测试期间禁止外部连接：%s" % (host,))
            return real_connect(self, address)

        socket.socket.connect = guard
        try:
            runner.run(_full_ctx())
        finally:
            socket.socket.connect = real_connect


class TargetScopeTests(unittest.TestCase):
    """SKILL.md：主目标 AI向量机 + 次要目标独立机；诱饵机时间盒。"""

    def test_secondary_target_runs_as_independent_machine(self):
        ctx = _full_ctx(secondary_targets=("h2",))
        runs = runner.run_targets(ctx)
        self.assertEqual([r.role for r in runs], ["AI向量机", "独立机"])
        self.assertEqual(runs[1].target, "h2")
        self.assertEqual([s.step_id for s in runs[1].report.steps], list(STEP_IDS))

    def test_decoy_stops_before_secondary_target(self):
        ctx = _full_ctx(secondary_targets=("h2",), decoy=True)
        runs = runner.run_targets(ctx)
        self.assertEqual(len(runs), 1)
        self.assertEqual(ctx.transport.calls, [])

    def test_inventory_endpoints_are_noted(self):
        ctx = _full_ctx(inventory_endpoints=("h:11434", "10.0.0.9:8000"))
        result = runner.run(ctx)
        self.assertTrue(any("recon-ai 资产清单" in n for n in result.notes))

    def test_decoy_timebox_stops_remaining_steps(self):
        ctx = _full_ctx(decoy_timebox_minutes=-1)
        result = runner.run(ctx)
        self.assertEqual(result.steps, [])
        self.assertTrue(any("时间盒耗尽" in n for n in result.notes))


class CliTests(unittest.TestCase):
    def test_dry_run_returns_zero(self):
        self.assertEqual(cli.main(["--target", "192.0.2.1", "--dry-run",
                                   "--ports", "11434"]), 0)

    def test_build_context_parses_ports_and_exec(self):
        parser = cli._build_parser()
        args = parser.parse_args(["--target", "h", "--ports", "11434,6443",
                                  "--exec-cmd", "id -a", "--step", "infra-01"])
        ctx = cli.build_context(args)
        self.assertEqual(ctx.ports, (11434, 6443))
        self.assertEqual(ctx.exec_argv, ("id", "-a"))
        self.assertEqual(ctx.step_ids, ("infra-01",))

    def test_build_context_wires_inventory_and_secondary(self):
        parser = cli._build_parser()
        args = parser.parse_args(["--target", "h", "--secondary-target", "h2",
                                  "--decoy-timebox", "15"])
        ctx = cli.build_context(args)
        self.assertEqual(ctx.secondary_targets, ("h2",))
        self.assertEqual(ctx.decoy_timebox_minutes, 15)

    def test_render_runs_covers_text_and_json(self):
        rep = model.RunReport(target="h")
        rep.steps.append(model.StepVerdict("infra-01", model.Outcome.EXPOSED_NO_AUTH,
                                           summary="hit", command="curl -s x"))
        runs = [runner.TargetRun("h", "AI向量机", rep),
                runner.TargetRun("h2", "独立机", model.RunReport(target="h2"))]
        text = cli.render_runs(runs)
        self.assertIn("### 目标 h（AI向量机）", text)
        self.assertIn("### 目标 h2（独立机）", text)
        payload = json.loads(cli.render_runs(runs, as_json=True))
        self.assertEqual([t["role"] for t in payload["targets"]], ["AI向量机", "独立机"])

    def test_invalid_step_exits_two(self):
        with self.assertRaises(SystemExit) as err:
            cli._build_parser().parse_args(["--target", "h", "--step", "infra-99"])
        self.assertEqual(err.exception.code, 2)

    def test_empty_target_is_usage_error(self):
        self.assertEqual(cli.main(["--target", " ", "--dry-run"]), 2)


if __name__ == "__main__":
    unittest.main()


class SkillGateTests(unittest.TestCase):
    """SKILL.md 执行体/质量门：脚本来源、截图标识、门禁阻断、独立机隔离。"""

    def test_five_steps_emit_script_source(self):
        ctx = _full_ctx()
        runner.run(ctx)
        records = {r["step_id"]: r for r in ctx.evidence.records}
        for sid in ("infra-02", "infra-03", "infra-04", "infra-05", "infra-06"):
            with self.subTest(step=sid):
                self.assertTrue(records[sid].get("script_src", "").startswith("https://"))
                self.assertTrue(records[sid].get("script_note"))
        self.assertNotIn("script_src", records["infra-01"])

    def test_shot_hook_has_target_and_timestamp(self):
        ctx = _full_ctx()
        runner.run(ctx)
        for record in ctx.evidence.records:
            self.assertIn("--headless=new", record["shot_cmd"])
            self.assertIn("--screenshot=", record["shot_cmd"])

    def test_evidence_failure_stops_following_steps(self):
        ctx = _full_ctx(evidence=FakeEvidence(exit_code=1, error="bad"))
        result = runner.run(ctx)
        self.assertEqual(len(result.steps), 1, "质量门未过不得进入下一步")
        self.assertIn("质量门未过", " ".join(result.notes))

    def test_secondary_target_writes_to_separate_dir(self):
        ctx = _full_ctx(secondary_targets=("192.0.2.9",))
        runs = runner.run_targets(ctx)
        self.assertEqual(len(runs), 2)
        self.assertEqual(runs[1].role, "独立机")
        self.assertEqual(runs[1].report.target, "192.0.2.9")
