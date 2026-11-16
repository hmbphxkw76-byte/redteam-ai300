#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""seam ③：证据落盘（委托共享容器，不重实现格式）。

单一事实源：片段结构、三件套/五件套判定、flag 双通道全部由
`tools/collect_evidence.py` 定义（canonical F-17）。本模块只把步骤执行结果
喂给它，因此 `report-exam` / CI 与本技能消费同一格式（C1 / AC-13）。
"""
import os
import subprocess
import sys
from typing import Dict, List, Tuple

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DEFAULT_TOOL = os.path.join(ROOT, "tools", "collect_evidence.py")


class EvidenceWriter:
    """生产实现：子进程调用共享收集器，保证行为与 CLI 完全一致。

    契约：符合 `tools/_evidence_contract.py#EvidenceWriterContract` 最小接口
    （describe / fragment_path / emit），由 scripts/check_evidence_contract.py 校验。
    本类为 skill 薄封装，构造签名与关键字别名保持不变。
    """

    def __init__(self, out_dir, manifest="", tool_path=DEFAULT_TOOL,
                 python=None, timeout=120):
        self.out_dir = out_dir
        self.manifest = manifest
        self.tool_path = tool_path
        self.python = python or sys.executable
        self.timeout = timeout

    def describe(self) -> str:
        return "collect_evidence.py (%s)" % os.path.basename(self.tool_path)

    def fragment_path(self, step_id) -> str:
        return os.path.join(self.out_dir, "%s.md" % step_id)

    def build_argv(self, step_id, command, output="", target="", title="",
                   screenshot="", shot_kind="", shot_cmd="", ai_log="",
                   flag="", flag_panel="", flag_shot="", note="", strict=True,
                   script="", script_src="", script_note=""):
        path = self.fragment_path(step_id)
        argv = [self.python, self.tool_path,
                "--step", step_id,
                "--cmd", command,
                "--out", path]
        if output:
            argv += ["--output", output]
        if target:
            argv += ["--target", target]
        if title:
            argv += ["--title", title]
        if screenshot:
            argv += ["--screenshot", screenshot]
        if shot_kind:
            argv += ["--shot-kind", shot_kind]
        if shot_cmd:
            argv += ["--shot-cmd", shot_cmd]
        if ai_log:
            argv += ["--ai-log", ai_log]
        if flag:
            argv += ["--flag", flag]
        if flag_panel:
            argv += ["--flag-panel", flag_panel]
        if flag_shot:
            argv += ["--flag-shot", flag_shot]
        if note:
            argv += ["--note", note]
        if script:
            argv += ["--script", script]
        if script_src:
            argv += ["--script-src", script_src]
        if script_note:
            argv += ["--script-note", script_note]
        if self.manifest:
            argv += ["--manifest", self.manifest]
        if strict:
            argv += ["--strict"]
        return argv

    def emit(self, step_id, command, output="", **kwargs) -> Tuple[str, int, str]:
        os.makedirs(self.out_dir, exist_ok=True)
        argv = self.build_argv(step_id, command, output=output, **kwargs)
        try:
            proc = subprocess.run(argv, capture_output=True, text=True,
                                  timeout=self.timeout, shell=False)
        except (OSError, subprocess.TimeoutExpired) as exc:
            return self.fragment_path(step_id), 2, str(exc)[:200]
        err = (proc.stderr or "").strip()[:400]
        return self.fragment_path(step_id), proc.returncode, err


class FakeEvidence:
    """测试替身：记录入参，不落盘（AC-19 离线可测）。"""

    def __init__(self, exit_code=0, error=""):
        self.exit_code = exit_code
        self.error = error
        self.records: List[Dict[str, str]] = []

    def describe(self) -> str:
        return "fake(%d records)" % len(self.records)

    def fragment_path(self, step_id) -> str:
        return "fake/%s.md" % step_id

    def build_argv(self, *args, **kwargs):  # pragma: no cover - 仅接口对齐
        return []

    def emit(self, step_id, command, output="", **kwargs):
        record = {"step_id": step_id, "command": command, "output": output}
        record.update({k: v for k, v in kwargs.items() if v})
        self.records.append(record)
        return self.fragment_path(step_id), self.exit_code, self.error
