#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""attack-multi-agent 编排器与 CLI 集成测试（S9 / AC-10..AC-15）。

用 FakeHttpClient + RecordingWriter + NullCapture 使整条路径离线可跑；
断言 8 步证据 1:1 落盘、定级诚实（capped/local_only/execution_error）、
证据质量门失败即抛错、CLI 薄壳可用。
"""
import contextlib
import io
import json
import unittest

from tools.pyrit_compat import TARGET_VERSION

import tools.attack_multi_agent as pkg
from tools.attack_multi_agent import Runtime, run_attack, AttackRequest, Scanner, BuiltinAnalyzer
from tools.attack_multi_agent import cli
from tools.attack_multi_agent.evidence import RecordingWriter
from tools.attack_multi_agent.shot import NullCapture
from tools.attack_multi_agent.transport import FakeHttpClient, Response

BODY = ("agent: agentA\nagent: agentB\nbus: kafka\n"
        "accepted executed deviated differ run")


def make_runtime(body=BODY, local_only=False, scanner=None):
    return Runtime(
        client=FakeHttpClient(default=Response(200, body, "application/json")),
        writer=RecordingWriter(), capture=NullCapture(),
        scanner=scanner or BuiltinAnalyzer(),
        shot_enabled=False, local_only=local_only)


def run(paths=("A", "B", "C"), step="", flag="AIVEC-xyz", emit=True, runtime=None):
    req = AttackRequest(target="http://t", paths=paths, step=step,
                        emit=emit, flag_value=flag)
    return run_attack(req, runtime or make_runtime())


class RunnerTests(unittest.TestCase):
    def test_full_run_all_eight_evidence(self):
        rep = run()
        self.assertEqual(len(rep.verdicts), 8)
        self.assertEqual([v.step_id for v in rep.verdicts], list(pkg.STEP_IDS))
        # 每步 1:1 落盘（RecordingWriter 返回路径）
        self.assertTrue(all(v.evidence_path for v in rep.verdicts))
        self.assertEqual(rep.by_step("a2a-08").observation.tool_result, "AIVEC-xyz")
        self.assertEqual(rep.object_graph["framework"][:12], "pyrit==" + TARGET_VERSION)

    def test_a2a08_panel_channel_gated_by_local_only(self):
        """审查 P6 收口：正式路径面板通道留空（vrf-04 阻断缺失），仅离线对照组等价双通道。"""
        for local_only, expected_panel in ((False, ""), (True, "AIVEC-xyz")):
            writer = RecordingWriter()
            rt = Runtime(
                client=FakeHttpClient(default=Response(200, BODY, "application/json")),
                writer=writer, capture=NullCapture(), scanner=BuiltinAnalyzer(),
                shot_enabled=False, local_only=local_only)
            run(runtime=rt)
            call = next(c for c in writer.calls if c["step_id"] == "a2a-08")
            self.assertEqual(call["flag_panel"], expected_panel)
            self.assertEqual(call["flag_shot"], "AIVEC-xyz")

    def test_paths_override_branch(self):
        # 触发 run_attack(paths=...) 重建 AttackRequest 的分支
        req = AttackRequest(target="http://t", paths=("A", "B", "C"),
                            emit=True, flag_value="F")
        rep = run_attack(req, make_runtime(), paths=("A",))
        self.assertEqual([v.step_id for v in rep.verdicts],
                         ["a2a-01", "a2a-02", "a2a-03", "a2a-08"])

    def test_capability_missing_single_agent(self):
        rep = run(paths=(), step="a2a-01", runtime=make_runtime(body="nothing here"))
        self.assertEqual(rep.by_step("a2a-01").level, "已跳过")

    def test_a2a_04_write_rejected_is_uneffective(self):
        # F2 回归：写入被拒（404）时不得因 before/after 恒不等而误判「部分生效」
        client = FakeHttpClient(
            script={"http://t/set": Response(404, "Not found", "text/plain",
                                             error="HTTP Error 404")},
            default=Response(200, "agent: agentA\nbus: kafka", "application/json"))
        rt = Runtime(client=client, writer=RecordingWriter(), capture=NullCapture(),
                     scanner=BuiltinAnalyzer(), shot_enabled=False)
        rep = run(step="a2a-04", runtime=rt)
        self.assertEqual(rep.by_step("a2a-04").level, "未生效")

    def test_local_only_capped(self):
        rep = run(runtime=make_runtime(local_only=True))
        # a2a-02 命中双信号，但 local_only 封顶为部分生效
        self.assertEqual(rep.by_step("a2a-02").level, "部分生效")

    def test_emit_false_no_evidence(self):
        rep = run(step="a2a-01", emit=False)
        self.assertEqual(rep.by_step("a2a-01").evidence_path, "")

    def test_scanner_error_is_execution_error(self):
        class Boom(Scanner):
            def analyze(self, text):
                raise ValueError("boom")

        rep = run(paths=(), step="a2a-01", runtime=make_runtime(scanner=Boom()))
        v = rep.by_step("a2a-01")
        self.assertEqual(v.level, "未生效")
        self.assertIn("执行异常", v.reason)

    def test_evidence_gate_failure_raises(self):
        class BadWriter:
            def emit(self, **kw):
                return "<mem>", 1, "missing-shot"

        rt = make_runtime()
        rt.writer = BadWriter()
        with self.assertRaises(RuntimeError):
            run(step="a2a-01", runtime=rt)

    def test_use_pyrit_passthrough(self):
        req = AttackRequest(target="http://t", paths=("A",), emit=True, use_pyrit=True)
        rep = run_attack(req, make_runtime())
        self.assertTrue(rep.request.use_pyrit)


class CliTests(unittest.TestCase):
    def setUp(self):
        self._saved = cli.Runtime
        cli.Runtime = lambda *a, **k: make_runtime()

    def tearDown(self):
        cli.Runtime = self._saved

    def test_json_output(self):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            code = cli.main(["http://t", "--paths", "A", "--json",
                             "--no-emit", "--no-shot", "--flag", "F"])
        self.assertEqual(code, 0)
        data = json.loads(buf.getvalue())
        self.assertEqual(data["target"], "http://t")
        self.assertTrue(data["verdicts"])

    def test_plain_output(self):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            code = cli.main(["http://t", "--step", "a2a-01", "--no-emit", "--no-shot"])
        self.assertEqual(code, 0)
        self.assertIn("a2a-01", buf.getvalue())


class PackageSurfaceTests(unittest.TestCase):
    def test_public_exports(self):
        for name in ("run_attack", "Runtime", "OBJECT_GRAPH", "AttackRequest",
                     "AttackReport", "LEVELS", "Scanner", "steps_for_paths"):
            self.assertTrue(hasattr(pkg, name), name)


if __name__ == "__main__":
    unittest.main()
