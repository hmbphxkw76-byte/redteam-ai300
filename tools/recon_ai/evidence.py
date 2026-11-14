#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""证据落盘 seam（S2）：委托共享收集器，不重实现格式。

单一事实源：片段结构、件套判定、flag 双通道、证据清单 JSONL 均由
`tools/collect_evidence.py` 定义；本模块只负责「把一次步骤的执行结果喂给它」。
这使得 `report-exam` / CI 与本技能消费同一格式，避免两套判据漂移（C1）。
"""
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DEFAULT_TOOL = os.path.join(ROOT, "tools", "collect_evidence.py")


class EvidenceWriter:
    """证据写入器：子进程调用共享收集器（保证行为与 CLI 完全一致）。"""

    def __init__(self, out_dir, manifest="", tool_path=DEFAULT_TOOL,
                 python=None, timeout=120):
        self.out_dir = out_dir
        self.manifest = manifest
        self.tool_path = tool_path
        self.python = python or sys.executable
        self.timeout = timeout

    def describe(self):
        return "collect_evidence.py (%s)" % os.path.basename(self.tool_path)

    def fragment_path(self, step_id):
        return os.path.join(self.out_dir, "%s.md" % step_id)

    def emit(self, step_id, command, output, target="", title="",
             screenshot="", shot_kind="", shot_cmd="", profile="",
             script="", script_src="", script_note="", strict=True,
             note="", ai_log=""):
        """写一份证据片段；返回 (片段路径, 退出码, 标准错误摘要)。

        退出码语义沿用共享工具：0 成功；1 严格模式未过质量门；2 用法错误。
        """
        os.makedirs(self.out_dir, exist_ok=True)
        out = self.fragment_path(step_id)
        cmd = [self.python, self.tool_path,
               "--step", step_id, "--cmd", command, "--out", out,
               "--output-file", "-", "--target", target, "--title", title]
        if screenshot:
            cmd += ["--screenshot", screenshot]
        if shot_kind:
            cmd += ["--shot-kind", shot_kind]
        if shot_cmd:
            cmd += ["--shot-cmd", shot_cmd]
        if profile:
            cmd += ["--profile", profile]
        if script:
            cmd += ["--script", script]
        if script_src:
            cmd += ["--script-src", script_src]
        if script_note:
            cmd += ["--script-note", script_note]
        if note:
            cmd += ["--note", note]
        if ai_log:
            cmd += ["--ai-log", ai_log]
        if self.manifest:
            cmd += ["--manifest", self.manifest]
        if strict:
            cmd += ["--strict"]
        proc = subprocess.run(cmd, input=output or "", capture_output=True,
                              text=True, encoding="utf-8", timeout=self.timeout)
        return out, proc.returncode, (proc.stderr or "").strip()


def load_manifest(path):
    """读取证据清单 JSONL（供 report-exam / 复核脚本复用，不重实现解析）。"""
    import json
    records = []
    if not path or not os.path.isfile(path):
        return records
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records
