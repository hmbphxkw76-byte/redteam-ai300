#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""attack-multi-agent 单元测试（S9 / AC-12..AC-14）。

覆盖：model / grade / steps / transport / a2a / scanner / evidence / shot / pyrit。
仅依赖标准库；外部依赖（HTTP、浏览器、pyrit、a2a-scanner）一律经缝注入替身或断言显式报错。
运行：python -m unittest discover -s tests -v
"""
import os
import tempfile
import unittest
import urllib.error
from unittest import mock

from tools.attack_multi_agent import (
    AttackReport, AttackRequest, BuiltinAnalyzer, LEVELS, Observation, Scanner,
    Signals, StepVerdict, find_flags, find_secrets, grade, message_accepted,
    parse_topology, redact, steps_for_paths, before_after_diff, derive,
    A2ASecBenchAdapter, AgentCardFinding, STEP_IDS)
from tools.attack_multi_agent.a2a import (
    A2ABusClient, MemoryStoreClient, OrchestratorClient)
from tools.attack_multi_agent.evidence import RecordingWriter
from tools.attack_multi_agent.pyrit_attack import run_pyrit_multiturn
from tools.attack_multi_agent import scanner as scanner_mod
from tools.attack_multi_agent.shot import (
    FakeCapture, HeadlessCapture, NullCapture, find_browser, make_capture,
    render_transcript)
from tools.attack_multi_agent.transport import (
    FakeHttpClient, Response, UrllibHttpClient)


class ModelTests(unittest.TestCase):
    def test_find_secrets_dedup_order(self):
        text = "a sk-ABCDEFGHIJKLMNOP1234 b sk-ABCDEFGHIJKLMNOP1234 c sk-ZYXWVUTSRQPONM5678"
        self.assertEqual(find_secrets(text),
                         ["sk-ABCDEFGHIJKLMNOP1234", "sk-ZYXWVUTSRQPONM5678"])
        self.assertEqual(find_secrets(""), [])

    def test_find_flags(self):
        self.assertEqual(find_flags("flag=abc123XYZ"), ["abc123XYZ"])
        self.assertEqual(find_flags("ai_vector: SECRET99"), ["SECRET99"])
        self.assertEqual(find_flags("none here"), [])

    def test_redact(self):
        self.assertIn("<REDACTED>", redact("sk-1234567890abc"))
        self.assertEqual(redact(""), "")
        self.assertIn("<REDACTED>", redact("short"))

    def test_parse_topology(self):
        topo = parse_topology("agent: agentA\nagent: agentB\nbus: kafka\nkey: conv:agentB")
        self.assertEqual(topo["agent_count"], 2)
        self.assertTrue(topo["bus_present"])
        self.assertIn("conv:agentB", topo["memory_keys"])
        empty = parse_topology("")
        self.assertEqual(empty["agent_count"], 0)
        self.assertFalse(empty["bus_present"])

    def test_parse_topology_ignores_prose(self):
        # F1 回归：SPA 文案「The AI agent you're supposed to break」不得被误判为 agent
        prose = "The AI agent you're supposed to break"
        self.assertEqual(parse_topology(prose)["agent_count"], 0)
        # 驼峰词 targetAgent 不得被当独立 agent 关键字（负向后顾）
        camel = '"targetAgent":"helperbot","name":"HelperBot"'
        self.assertEqual(parse_topology(camel)["agent_count"], 0)
        # 冒号分隔的显式声明仍须命中
        self.assertEqual(parse_topology("agent: securebot")["agents"], ("securebot",))

    def test_message_accepted_and_diff(self):
        self.assertTrue(message_accepted("accepted"))
        self.assertTrue(message_accepted("已接收"))
        self.assertFalse(message_accepted("nope"))
        self.assertTrue(before_after_diff("a", "b"))
        self.assertFalse(before_after_diff("a", "a"))
        self.assertFalse(before_after_diff(None, "x"))
        self.assertFalse(before_after_diff("", "x"))

    def test_observation_secrets_and_dict(self):
        obs = Observation(text="t", tool_result="sk-ABCDEFGHIJKLMNOP1234")
        self.assertEqual(obs.secrets, ["sk-ABCDEFGHIJKLMNOP1234"])
        d = obs.as_dict()
        self.assertIn("secrets", d)
        # 元数据 secrets 已脱敏；原文仅保留在 tool_result 作为证据
        self.assertNotIn("sk-ABCDEFGHIJKLMNOP1234", d["secrets"][0])
        self.assertIn("<REDACTED>", d["secrets"][0])

    def test_attack_request_defaults_and_report(self):
        req = AttackRequest(target="http://t")
        self.assertEqual(req.paths, ("A", "B", "C"))
        self.assertEqual(req.mode, "a2a-bus")
        self.assertEqual(req.flag_value, "")
        v = StepVerdict("a2a-01", "", "t", "未生效", "r", "c", Observation())
        rep = AttackReport(request=req, backend="fake", verdicts=(v,))
        self.assertEqual(rep.levels(), ("未生效",))
        self.assertEqual(rep.evidence_paths(), ("",))
        self.assertIs(rep.by_step("a2a-01"), v)
        self.assertIsNone(rep.by_step("a2a-99"))
        self.assertEqual(rep.as_dict()["target"], "http://t")


class GradeTests(unittest.TestCase):
    def test_four_levels(self):
        self.assertEqual(grade(Signals("x", True, True))[0], "完全生效")
        self.assertEqual(grade(Signals("x", True, False))[0], "部分生效")
        self.assertEqual(grade(Signals("x", False, True))[0], "部分生效")
        self.assertEqual(grade(Signals("x", False, False))[0], "未生效")
        self.assertEqual(grade(Signals("x", capability_missing=True))[0], "已跳过")

    def test_caps(self):
        self.assertEqual(grade(Signals("x", True, True, consent_required=True))[0], "部分生效")
        self.assertEqual(grade(Signals("x", True, True, capped_partial=True))[0], "部分生效")
        self.assertIn("最高判部分生效", grade(Signals("x", True, True, capped_partial=True))[1])

    def test_derive_all_steps(self):
        obs = Observation(text="accepted executed deviated differ")
        for sid in STEP_IDS:
            sig = derive(sid, obs, {"oracle_success": True, "flag_value": "F",
                                    "flag_panel": "F", "downstream_acted": True,
                                    "impersonation_accepted": True,
                                    "memory_written": True, "memory_changed": True,
                                    "context_injected": True, "context_deviated": True,
                                    "task_spoofed_accepted": True, "workflow_deviated": True,
                                    "trace_diff_present": True, "decision_changed": True,
                                    "ai_log_present": True, "topology": {"agent_count": 2}})
            self.assertIn(sig.step_id, STEP_IDS)

    def test_derive_special(self):
        self.assertTrue(derive("a2a-01", None, {"execution_error": True}).detail)
        self.assertTrue(derive("a2a-01", None, {"capability_missing": True}).capability_missing)
        self.assertTrue(derive("bogus", None, {}).capability_missing)


class StepsTests(unittest.TestCase):
    def test_full_and_slice(self):
        full = steps_for_paths(("A", "B", "C"))
        self.assertEqual([s.step_id for s in full],
                         ["a2a-01", "a2a-02", "a2a-03", "a2a-04",
                          "a2a-05", "a2a-06", "a2a-07", "a2a-08"])
        self.assertEqual([s.step_id for s in steps_for_paths(("A",))],
                         ["a2a-01", "a2a-02", "a2a-03", "a2a-08"])
        self.assertEqual([s.step_id for s in steps_for_paths((), step="a2a-03")],
                         ["a2a-03"])

    def test_unknown_step_raises(self):
        with self.assertRaises(ValueError):
            steps_for_paths((), step="a2a-99")


class TransportTests(unittest.TestCase):
    def test_fake_client(self):
        fake = FakeHttpClient(script={"http://a": Response(200, "ok", "json")},
                              default=Response(201, "d", "json"))
        self.assertEqual(fake.request("GET", "http://a/x").body, "ok")
        self.assertEqual(fake.request("GET", "http://b").status, 201)
        self.assertEqual(len(fake.calls), 2)
        self.assertEqual(fake.describe(), "fake")

    def test_urllib_success(self):
        class Resp:
            status = 200
            headers = {"Content-Type": "application/json"}

            def read(self):
                return b'{"ok":true}'

            def __enter__(self):
                return self

            def __exit__(self, *a):
                return False

        with mock.patch("urllib.request.urlopen", return_value=Resp()):
            r = UrllibHttpClient().request("GET", "http://x")
        self.assertEqual(r.status, 200)
        self.assertTrue(r.ok())

    def test_urllib_http_and_os_error(self):
        with mock.patch("urllib.request.urlopen",
                        side_effect=urllib.error.HTTPError("u", 404, "nf", {}, None)):
            r = UrllibHttpClient().request("GET", "http://x")
        self.assertEqual(r.status, 404)
        with mock.patch("urllib.request.urlopen", side_effect=urllib.error.URLError("boom")):
            r2 = UrllibHttpClient().request("GET", "http://x")
        self.assertEqual(r2.status, 0)
        self.assertTrue(r2.error)


class A2AClientTests(unittest.TestCase):
    def _client(self, body="agent: agentA\nbus: kafka"):
        return FakeHttpClient(default=Response(200, body, "application/json"))

    def test_bus_actions(self):
        bus = A2ABusClient(self._client(), "http://t")
        obs, cmd, topo = bus.discover_topology()
        self.assertIn("curl", cmd)
        self.assertEqual(topo["agent_count"], 1)
        obs2, cmd2 = bus.inject_message("a", "b", "x")
        self.assertIn("curl", cmd2)
        self.assertEqual(obs2.request["body"]["from"], "a")
        obs3, cmd3 = bus.impersonate("a", "run")
        self.assertIn("/agent/a/cmd", cmd3)

    def test_memory_and_orchestrator(self):
        mem = MemoryStoreClient(self._client("before"), "http://t")
        before, cmd = mem.read_memory("k")
        self.assertEqual(before, "before")
        self.assertIn("curl", cmd)
        obs, cmd2 = mem.poison_memory("k", "v")
        self.assertIn("curl", cmd2)
        obs2, cmd3 = mem.poison_context("http://t/ctx", "inj")
        self.assertIn("curl", cmd3)
        orch = OrchestratorClient(self._client("run differ"), "http://t")
        obs3, cmd4 = orch.disrupt_workflow("task")
        self.assertIn("curl", cmd4)
        obs4, cmd5 = orch.get_trace("r1")
        self.assertIn("curl", cmd5)


class ScannerTests(unittest.TestCase):
    def test_builtin(self):
        findings = BuiltinAnalyzer().analyze(
            "scope: admin\ninstruction: 执行\nexfil http://evil")
        cats = {f.category for f in findings}
        self.assertIn("over-broad-scope", cats)
        self.assertIn("hidden-instruction", cats)
        self.assertIn("unexpected-egress", cats)
        self.assertEqual(BuiltinAnalyzer().analyze("clean text"), [])

    def test_adapter(self):
        adapter = A2ASecBenchAdapter(runner=lambda t: [
            {"category": "malicious-agent-card", "detail": "d", "severity": "high"}])
        out = adapter.analyze("t")
        self.assertEqual(out[0].category, "malicious-agent-card")
        self.assertEqual(out[0].severity, "high")

    def test_adapter_without_runner_raises(self):
        with self.assertRaises((RuntimeError, NotImplementedError)):
            A2ASecBenchAdapter().analyze("t")

    def test_describe(self):
        self.assertEqual(BuiltinAnalyzer().describe(), "BuiltinAnalyzer")
        self.assertIsInstance(Scanner(), Scanner)


class EvidenceShotTests(unittest.TestCase):
    def test_recording_writer(self):
        w = RecordingWriter()
        path, code, err = w.emit(step_id="a2a-01", command="c")
        self.assertEqual(code, 0)
        self.assertTrue(path)
        self.assertEqual(w.describe(), "recording")
        self.assertIn("a2a-01", w.fragment_path("a2a-01"))

    def test_render_transcript(self):
        html = render_transcript("CMD", "RESP", "http://t", "2026", "a2a-01")
        for token in ("a2a-01", "http://t", "2026", "CMD", "RESP"):
            self.assertIn(token, html)

    def test_captures(self):
        self.assertEqual(NullCapture().capture("s", "t", "."), ("", ""))
        self.assertIsInstance(make_capture(False), NullCapture)
        self.assertIsInstance(find_browser(), str)
        self.assertEqual(HeadlessCapture(browser_path="").capture("s", "t", "."), ("", ""))
        d = tempfile.mkdtemp()
        path, kind = FakeCapture().capture("a2a-01", "t", d)
        self.assertTrue(os.path.isfile(path))
        self.assertEqual(kind, "transcript")

    def test_headless_capture_success(self):
        d = tempfile.mkdtemp()
        cap = HeadlessCapture(browser_path="/bin/fake-browser")

        def fake_run(argv, **kw):
            for a in argv:
                if isinstance(a, str) and a.startswith("--screenshot="):
                    with open(a.split("=", 1)[1], "wb") as f:
                        f.write(b"PNGDATA")
            return mock.Mock(returncode=0)

        with mock.patch("tools.attack_multi_agent.shot.subprocess.run",
                        side_effect=fake_run):
            path, kind = cap.capture("a2a-01", "http://t", d)
        self.assertTrue(path and os.path.isfile(path))
        self.assertEqual(kind, "transcript")


class PyritSeamTests(unittest.TestCase):
    def test_lazy_import_error(self):
        try:
            import pyrit  # noqa: F401
        except ImportError:
            with self.assertRaises(RuntimeError):
                run_pyrit_multiturn("http://x", ["o"])
        else:
            self.skipTest("pyrit 已安装，跳过未安装分支")


if __name__ == "__main__":
    unittest.main()
