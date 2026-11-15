#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""S1 证据契约 seam：转发共享 `tools/collect_evidence.py`（AC-10~AC-16）。

不重造证据格式，只组装命令行；`runner(args)->CompletedProcess` 注入点供测试。
PyRIT 仅以 `SQLiteMemory` 做证据编排（惰性导入），禁止 `pyrit.orchestrator`。
"""
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
COLLECT = os.path.join(ROOT, "tools", "collect_evidence.py")


def _default_runner(args):
    return subprocess.run(args, capture_output=True, text=True)


def build_args(step, cmd, out, shot_cmd=None, ai_log=None, flag=None,
               target=None, strict=True):
    """组装 collect_evidence.py 命令行参数（纯函数，可单测）。"""
    args = [sys.executable, COLLECT, "--step", step, "--cmd", cmd, "--out", out]
    if target:
        args += ["--target", target]
    if shot_cmd:
        args += ["--shot-cmd", shot_cmd]
    if ai_log:
        args += ["--ai-log", ai_log]
    if flag:
        args += ["--flag", flag]
    if strict:
        args.append("--strict")
    return args


def emit(step, cmd, out, shot_cmd=None, ai_log=None, flag=None, target=None,
         strict=True, runner=None):
    """产出证据片段；返回 runner 结果（默认 CompletedProcess）。"""
    runner = runner or _default_runner
    return runner(build_args(step, cmd, out, shot_cmd, ai_log, flag, target, strict))
