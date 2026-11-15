#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""证据落盘 seam：委托共享收集器，不重实现格式（C1）。

片段结构、三件套判定、flag 双通道、证据清单 JSONL 均由
`tools/collect_evidence.py` 定义；本模块只负责把「一次判定步骤」喂给它
（与 `tools/recon_ai/evidence.py` 同一子进程适配模式）。这使 `report-exam` /
CI 与本技能消费同一格式，避免两套判据漂移。
"""
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DEFAULT_TOOL = os.path.join(ROOT, "tools", "collect_evidence.py")


class EvidenceWriter:
    """证据写入器：子进程调用共享收集器（行为与 CLI 完全一致）。"""

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
             note="", strict=True):
        """写一份证据片段；返回 (片段路径, 退出码, 标准错误摘要)。"""
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
        if note:
            cmd += ["--note", note]
        if self.manifest:
            cmd += ["--manifest", self.manifest]
        if strict:
            cmd += ["--strict"]
        proc = subprocess.run(cmd, input=output or "", capture_output=True,
                              text=True, encoding="utf-8", timeout=self.timeout)
        return out, proc.returncode, (proc.stderr or "").strip()
