"""D11 旁路网关测试。"""
from __future__ import annotations

import unittest

from tools.osai_orchestrator.d11_gateway import (
    D11Result, RunOutcome, SubprocessRunner, load_window,
    prepare_report_inputs, run_d11_gateway,
)
from tools.osai_orchestrator.models import GateResult, Verdict


class FakeRunner:
    def __init__(self, code: int) -> None:
        self.code = code
        self.calls: list[list[str]] = []

    def run(self, argv):
        self.calls.append(list(argv))
        return RunOutcome(self.code)


class GatewayTest(unittest.TestCase):
    def test_prepare_inputs_derives_flags_and_recon(self):
        registry = "| L-1 | flag | X | host2 | loot/a.md | t | 已取证 | 面板=P1；截图=e/a.png |"
        frags = [{"step": "recon-01", "host": "host2", "source": "synthetic"},
                 {"step": "trad-01", "host": "host2", "source": "real"}]
        flags, mapped = prepare_report_inputs(registry, frags, ["host2"])
        self.assertEqual(flags, {"host2": "P1"})
        self.assertEqual(len(mapped), 1)
        self.assertEqual(mapped[0]["step"], "recon-01")

    def test_gateway_blocks_when_window_missing(self):
        frags = [{"step": "recon-01", "host": "host2", "source": "synthetic"}]
        result = run_d11_gateway("", frags, ["host2"], window=None, encrypted=False)
        self.assertIs(result.submission_gate.verdict, Verdict.BLOCKED)

    def test_gateway_passes_full_inputs(self):
        registry = "| L-1 | flag | X | host2 | loot/a.md | t | 已取证 | 面板=P1；截图=e/a.png |"
        frags = [{"step": "recon-01", "host": "host2", "source": "synthetic"},
                 {"step": "trad-01", "host": "host2", "source": "real"}]
        window = {"exam_end_at": "2026-11-24T10:00:00Z", "submit_at": "2026-11-24T11:00:00Z"}
        # 无 runner / report_path 时资产检查未执行，H6 应为 BLOCKED（诚实边界）。
        result = run_d11_gateway(registry, frags, ["host2"], window=window, encrypted=False)
        self.assertIs(result.submission_gate.verdict, Verdict.BLOCKED)
        runner = FakeRunner(0)
        with __import__("tempfile").NamedTemporaryFile(suffix=".md", delete=False) as f:
            result = run_d11_gateway(registry, frags, ["host2"], report_path=f.name,
                                     window=window, encrypted=False, runner=runner)
        self.assertIs(result.report_gate.verdict, Verdict.PASS)
        self.assertIs(result.submission_gate.verdict, Verdict.PASS)
        self.assertTrue(result.passed)

    def test_gateway_calls_asset_check_when_runner_given(self):
        import tempfile
        frags = [{"step": "recon-01", "host": "host2", "source": "synthetic"}]
        window = {"exam_end_at": "a", "submit_at": "b"}
        with tempfile.NamedTemporaryFile(suffix=".md", delete=False) as f:
            path = f.name
        runner = FakeRunner(0)
        result = run_d11_gateway("", frags, ["host2"], report_path=path,
                                 window=window, encrypted=False, runner=runner)
        self.assertTrue(runner.calls)
        self.assertIn("check_report_assets.py", " ".join(runner.calls[0]))

    def test_load_window_missing(self):
        self.assertIsNone(load_window("/nonexistent/window.json"))

    def test_load_window_valid(self):
        import json
        import tempfile
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as f:
            json.dump({"exam_end_at": "a", "submit_at": "b"}, f)
            path = f.name
        data = load_window(path)
        self.assertEqual(data["exam_end_at"], "a")

    def test_d11_result_passed_requires_both(self):
        gate = GateResult("x", Verdict.PASS)
        r = D11Result({}, gate, gate)
        self.assertTrue(r.passed)


if __name__ == "__main__":
    unittest.main()
