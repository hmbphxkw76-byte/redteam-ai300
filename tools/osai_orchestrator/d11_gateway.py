"""D11 tracer bullet：报告提交边界的旁路网关。

只调用既有工具入口（report_exam / check_report_assets / verify_evidence），
不修改其语义、不重写判据。所有目标值为调用方注入。
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from .handoff import (
    derive_panel_flags,
    recon_fragments_for_report,
    check_h5_report_enumeration,
    check_h6_submission,
)
from .models import GateResult, Verdict


class CommandRunner(Protocol):
    def run(self, argv) -> object:
        ...


@dataclass
class RunOutcome:
    returncode: int
    stdout: str = ""
    stderr: str = ""


class SubprocessRunner:
    def run(self, argv) -> RunOutcome:
        import subprocess
        try:
            proc = subprocess.run(list(argv), capture_output=True, text=True)
        except FileNotFoundError as exc:
            return RunOutcome(127, "", str(exc))
        return RunOutcome(proc.returncode, proc.stdout or "", proc.stderr or "")


@dataclass
class D11Result:
    panel_flags: dict[str, str]
    report_gate: GateResult
    submission_gate: GateResult

    @property
    def passed(self) -> bool:
        return self.report_gate.ok and self.submission_gate.ok


def prepare_report_inputs(registry_text: str, fragments: list[dict],
                          hosts: list[str]) -> tuple[dict[str, str], list[dict]]:
    """旁路产出 assemble_report 所需输入：派生 panel_flags + 映射侦察片段。"""
    flags = derive_panel_flags(registry_text)
    mapped = recon_fragments_for_report(fragments, hosts)
    return flags, mapped


def run_d11_gateway(registry_text: str, fragments: list[dict], hosts: list[str],
                    report_path: str | None = None,
                    window: dict | None = None,
                    encrypted: bool | None = None,
                    runner: CommandRunner | None = None) -> D11Result:
    """D11 组合入口：H5 报告证据 + H6 提交门禁。不触发真实提交。"""
    flags, mapped = prepare_report_inputs(registry_text, fragments, hosts)
    recon_steps = [f.get("step", "") for f in mapped]
    report_steps = [f.get("step", "") for f in fragments]
    report_gate = check_h5_report_enumeration(report_steps, recon_steps, hosts)

    assets_ok = False
    if report_path and Path(report_path).is_file() and runner is not None:
        outcome = runner.run(["python", "scripts/check_report_assets.py", report_path])
        assets_ok = getattr(outcome, "returncode", 1) == 0

    window_ok = bool(window and window.get("exam_end_at") and window.get("submit_at"))
    encryption_ok = encrypted is False
    submission_gate = check_h6_submission(assets_ok, window_ok, encryption_ok)
    return D11Result(flags, report_gate, submission_gate)


def load_window(path: str) -> dict | None:
    """读取时间锚文件；不存在返回 None，不用系统时间代替。"""
    p = Path(path)
    if not p.is_file():
        return None
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return data if isinstance(data, dict) else None
