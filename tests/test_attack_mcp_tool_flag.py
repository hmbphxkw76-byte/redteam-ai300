#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""attack-mcp-tool flag 双通道与证据契约测试（规格 v2 AC-12/13/14/15/16）。

flag 分支必须双向断言：可取到值 → 面板提交值 == 正文回显值；
取不到值 → 判「已跳过」且不得出现任何占位 flag（禁止伪造）。
"""
import json
import os
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from tools.attack_mcp_tool import AttackRequest, Runtime, run_attack  # noqa: E402
from tools.attack_mcp_tool.evidence import EvidenceWriter, RecordingWriter, load_manifest  # noqa: E402
from tools.attack_mcp_tool.shot import NullCapture  # noqa: E402
from tools.attack_mcp_tool.transport import FakeHttpClient, HttpResponse  # noqa: E402

SECRET = "sk-QWERTYuiop1234567890ab"


def sse(tool_result="", telemetry=None, chunks=()):
    lines = ["event: meta", 'data: {"lab_id": "MCP_01", "phase": 4}']
    for c in chunks:
        lines += ["", 'data: {"content": %s}' % json.dumps(c, ensure_ascii=False)]
    lines += ["", "event: mcp_result",
              "data: %s" % json.dumps({"tool_result": tool_result,
                                       "mcp_telemetry": telemetry or {}},
                                      ensure_ascii=False)]
    return "\n".join(lines) + "\n"


def routes_for(secret=SECRET, oracle=True):
    return {
        ("POST", "http://t.example/api/labs/MCP_01/chat"):
            HttpResponse(status=200, body=sse(tool_result='{"service_token": "%s"}' % secret,
                                              telemetry={"selected_tool": "get_config",
                                                         "permissions_used": ["read"],
                                                         "policy_decision": "allowed",
                                                         "exploit_success": True})),
        ("POST", "http://t.example/api/secrets/validate"):
            HttpResponse(status=200,
                         body=json.dumps({"success": oracle, "message": "ok"})),
    }


class FlagChannelTests(unittest.TestCase):
    """AC-14 / AC-15：双通道与禁止伪造。"""

    def test_ac14_oracle_accepts_value_counts_as_consistent(self):
        writer = RecordingWriter()
        runtime = Runtime(client=FakeHttpClient(routes_for()), writer=writer,
                          capture=NullCapture())
        report = run_attack(AttackRequest(target="http://t.example", step="mcp-08"), runtime)
        verdict = report.verdicts[0]
        self.assertEqual(verdict.level, "完全生效")
        call = writer.calls[0]
        self.assertEqual(call["flag_panel"], SECRET)
        self.assertEqual(call["flag_shot"], SECRET, "面板值与正文值必须一致")
        self.assertIn("ai_vector.txt", call["note"], "降级依据必须写入注记")

    def test_ac14_oracle_rejects_value_downgrades(self):
        runtime = Runtime(client=FakeHttpClient(routes_for(oracle=False)),
                          writer=RecordingWriter(), capture=NullCapture())
        report = run_attack(AttackRequest(target="http://t.example", step="mcp-08"), runtime)
        self.assertEqual(report.verdicts[0].level, "部分生效")

    def test_ac15_no_value_means_skip_and_no_flag_injected(self):
        body = sse(tool_result='{"error": "no token"}')
        runtime = Runtime(client=FakeHttpClient({
            ("POST", "http://t.example/api/labs/MCP_01/chat"):
                HttpResponse(status=200, body=body)}),
            writer=RecordingWriter(), capture=NullCapture())
        report = run_attack(AttackRequest(target="http://t.example", step="mcp-08"), runtime)
        verdict = report.verdicts[0]
        self.assertEqual(verdict.level, "已跳过")
        call = runtime.writer.calls[0]
        self.assertEqual(call["flag_panel"], "")
        self.assertEqual(call["flag_shot"], "")
        self.assertIn("不伪造", call["note"])


class EvidenceContractTests(unittest.TestCase):
    """AC-12 / AC-13 / AC-16：片段结构、截图降级、清单字段。"""

    def _run(self, tmp, capture=None):
        writer = EvidenceWriter(tmp, manifest=os.path.join(tmp, "manifest.jsonl"))
        runtime = Runtime(client=FakeHttpClient(routes_for()), writer=writer,
                          capture=capture or NullCapture())
        return run_attack(AttackRequest(target="http://t.example", step="mcp-08"), runtime)

    def test_ac12_fragment_has_four_required_sections(self):
        with tempfile.TemporaryDirectory() as tmp:
            report = self._run(tmp)
            with open(report.verdicts[0].evidence_path, encoding="utf-8") as f:
                text = f.read()
        for section in ("#### 确切命令", "#### 关键输出", "#### 截图（访问证明）",
                        "#### 证据校验（五件套 / 三件套）"):
            self.assertIn(section, text)

    def test_ac13_no_browser_marks_pending_and_writes_no_png(self):
        with tempfile.TemporaryDirectory() as tmp:
            report = self._run(tmp)
            with open(report.verdicts[0].evidence_path, encoding="utf-8") as f:
                text = f.read()
            pngs = [n for n in os.listdir(tmp) if n.endswith(".png")]
        self.assertIn("待补录", text)
        self.assertEqual(pngs, [], "无浏览器时不得生成任何截图文件")

    def test_ac16_manifest_row_has_required_fields(self):
        with tempfile.TemporaryDirectory() as tmp:
            self._run(tmp)
            records = load_manifest(os.path.join(tmp, "manifest.jsonl"))
        self.assertEqual(len(records), 1)
        for key in ("step_id", "command", "sha256", "timestamp", "pieces", "complete"):
            self.assertIn(key, records[0])
        self.assertTrue(records[0]["complete"], "三件套必须齐全（strict 已通过）")
        self.assertEqual(records[0]["step_id"], "mcp-08")


class AllStepsEvidenceTests(unittest.TestCase):
    """AC-12 全量：八步都必须经共享工具落盘且四节齐全、strict 退出码 0。"""

    def test_all_eight_steps_emit_complete_fragments(self):
        default = HttpResponse(status=200, content_type="text/event-stream",
                               body=sse(tool_result="", telemetry={}, chunks=["no tools"]))
        routes = dict(routes_for())
        routes[("GET", "http://t.example/")] = HttpResponse(
            status=200, content_type="text/html", body="<html></html>")
        for name in ("/ai_vector.txt", "/proof.txt", "/static/ai_vector.txt"):
            routes[("GET", "http://t.example" + name)] = HttpResponse(
                status=200, content_type="text/html", body="<html></html>")
        with tempfile.TemporaryDirectory() as tmp:
            writer = EvidenceWriter(tmp, manifest=os.path.join(tmp, "manifest.jsonl"))
            runtime = Runtime(client=FakeHttpClient(routes, default=default),
                              writer=writer, capture=NullCapture())
            report = run_attack(AttackRequest(target="http://t.example"), runtime)
            self.assertEqual(len(report.verdicts), 8)
            for verdict in report.verdicts:
                with open(verdict.evidence_path, encoding="utf-8") as f:
                    text = f.read()
                with self.subTest(step=verdict.step_id):
                    self.assertIn("#### 确切命令", text)
                    self.assertIn("#### 关键输出", text)
                    self.assertIn("#### 截图（访问证明）", text)
            records = load_manifest(os.path.join(tmp, "manifest.jsonl"))
        self.assertEqual(len(records), 8)
        self.assertTrue(all(r["complete"] for r in records))

    def test_ai_log_only_for_steps_that_prompt_the_model(self):
        """§6.3 真实性：未向目标发提示的步骤不得出现 AI 交互日志（防跨步臆造）。"""
        default = HttpResponse(status=200, content_type="text/event-stream",
                               body=sse(tool_result="", telemetry={}))
        routes = {("GET", "http://t.example/"): HttpResponse(
            status=200, content_type="text/html", body="<html></html>")}
        with tempfile.TemporaryDirectory() as tmp:
            writer = RecordingWriter()
            runtime = Runtime(client=FakeHttpClient(routes, default=default),
                              writer=writer, capture=NullCapture())
            run_attack(AttackRequest(target="http://t.example"), runtime)
        prompted = {c["step_id"]: bool(c["ai_log"]) for c in writer.calls}
        for step_id in ("mcp-02", "mcp-04"):
            self.assertFalse(prompted[step_id],
                             "%s 未发送提示，不得臆造 AI 交互日志" % step_id)
        for step_id in ("mcp-01", "mcp-05", "mcp-07", "mcp-08"):
            self.assertTrue(prompted[step_id], "%s 应记录模型交互" % step_id)


if __name__ == "__main__":
    unittest.main()
