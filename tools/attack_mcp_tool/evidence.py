#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""证据落盘 seam（S2）：委托共享收集器，不重实现格式。

单一事实源：片段结构、件套判定、flag 双通道、证据清单 JSONL 均由
`tools/collect_evidence.py` 定义；本模块只负责「把一次步骤的执行结果喂给它」（C1）。
"""
import json
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DEFAULT_TOOL = os.path.join(ROOT, "tools", "collect_evidence.py")


class EvidenceWriter:
    """子进程调用共享收集器，保证行为与 CLI 完全一致。"""

    def __init__(self, out_dir, manifest="", tool_path=DEFAULT_TOOL,
                 python=None, timeout=180):
        self.out_dir = out_dir
        self.manifest = manifest
        self.tool_path = tool_path
        self.python = python or sys.executable
        self.timeout = timeout

    def describe(self):
        return "collect_evidence.py"

    def fragment_path(self, step_id):
        return os.path.join(self.out_dir, "%s.md" % step_id)

    def emit(self, step_id, command, output, target="", title="", screenshot="",
             shot_kind="", shot_cmd="", profile="", script="", script_src="",
             script_note="", strict=True, note="", ai_log="", flag_panel="",
             flag_shot="", flag=""):
        """写一份证据片段；返回 (片段路径, 退出码, 标准错误摘要)。"""
        os.makedirs(self.out_dir, exist_ok=True)
        out = self.fragment_path(step_id)
        argv = [self.python, self.tool_path, "--step", step_id, "--cmd", command,
                "--out", out, "--output-file", "-", "--target", target,
                "--title", title]
        for key, value in (("--screenshot", screenshot), ("--shot-kind", shot_kind),
                           ("--shot-cmd", shot_cmd), ("--profile", profile),
                           ("--script", script), ("--script-src", script_src),
                           ("--script-note", script_note), ("--note", note),
                           ("--ai-log", ai_log), ("--flag", flag),
                           ("--flag-panel", flag_panel), ("--flag-shot", flag_shot)):
            if value:
                argv += [key, value]
        if self.manifest:
            argv += ["--manifest", self.manifest]
        if strict:
            argv.append("--strict")
        proc = subprocess.run(argv, input=output or "", capture_output=True,
                              text=True, encoding="utf-8", timeout=self.timeout)
        return out, proc.returncode, (proc.stderr or "").strip()


class RecordingWriter:
    """测试替身：只记录调用参数，不写盘（用于断言证据契约）。"""

    def __init__(self):
        self.calls = []

    def describe(self):
        return "recording"

    def fragment_path(self, step_id):
        return "<memory>/%s.md" % step_id

    def emit(self, **kwargs):
        self.calls.append(kwargs)
        return self.fragment_path(kwargs.get("step_id", "")), 0, ""


def load_manifest(path):
    """读取证据清单 JSONL（供复核脚本复用，不重实现解析）。"""
    records = []
    if not path or not os.path.isfile(path):
        return records
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records
