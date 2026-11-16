#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""证据片段生产端：委托共享 `collect_evidence.py`，不重实现格式（C1）。

每步以 `--step cr-NN --strict` 落盘三件套（确切命令 / 关键输出 / 截图钩子）
并附 AI 交互日志；本技能不取 flag，双通道保持 N/A 而非伪造（AC-21）。
截图用 `--shot-cmd` 记录捕获钩子，不自行捕获、不伪造截图。
"""
from __future__ import annotations

import os
import subprocess
import sys
from typing import Iterable, Tuple

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
COLLECTOR = os.path.join(ROOT, "tools", "collect_evidence.py")

# (step_id, 标题, 截图捕获钩子)
STEPS = (
    ("cr-01", "九阶段覆盖度矩阵", "edge --headless=new --screenshot=cr-01.png <演练面板>"),
    ("cr-02", "24h 节奏时间线", "edge --headless=new --screenshot=cr-02.png <时间线视图>"),
    ("cr-03", "缺口清单与分级", "edge --headless=new --screenshot=cr-03.png <缺口视图>"),
    ("cr-04", "证据链贯通核对", "edge --headless=new --screenshot=cr-04.png <片段索引>"),
    ("cr-05", "演练报告四件产出", "edge --headless=new --screenshot=cr-05.png <报告预览>"),
    ("cr-06", "机读结果与退出码", "edge --headless=new --screenshot=cr-06.png <CLI 输出>"),
)
AI_LOG_NOTE = ("模型：本次走查由确定性判据执行，未调用 LLM 评分；"
               "AI 辅助仅用于文档措辞，采纳结果经人工复核（§5.5）。")


class EvidenceWriter:
    """证据写入器：子进程调用共享收集器（与 decoy_detect 同一适配模式）。"""

    def __init__(self, out_dir: str, python: str = None,
                 collector: str = COLLECTOR, root: str = ROOT):
        self.out_dir = out_dir
        self.python = python or sys.executable
        self.collector = collector
        self.root = root

    def describe(self) -> str:
        return "collect_evidence.py (%s)" % os.path.basename(self.collector)

    def fragment_path(self, step_id: str) -> str:
        return os.path.join(self.out_dir, "%s.md" % step_id)

    def emit(self, step_id: str, command: str, output: str, title: str,
             shot_cmd: str, strict: bool = True) -> Tuple[str, int, str]:
        os.makedirs(self.out_dir, exist_ok=True)
        out = self.fragment_path(step_id)
        cmd = [self.python, self.collector,
               "--step", step_id, "--cmd", command, "--out", out,
               "--output", output, "--title", title, "--target", "drill-target",
               "--profile", "rehearsal", "--shot-cmd", shot_cmd,
               "--ai-log", AI_LOG_NOTE,
               "--note", "演练/仿真片段，非 OSAI 正式考试证据。"]
        if strict:
            cmd.append("--strict")
        proc = subprocess.run(cmd, capture_output=True, text=True,
                              encoding="utf-8", cwd=self.root, timeout=120)
        return out, proc.returncode, (proc.stderr or "").strip()

    def emit_all(self) -> Tuple[Tuple[str, ...], int]:
        """逐步实际执行 CLI 单步摘要，捕获真实 stdout 作为关键输出。

        命令字符串保留为可 copy/paste 形式；执行用 argv 列表，避免路径含空格时
        shell 解析差异（Git Bash / Windows 一致）。
        """
        paths, failures = [], 0
        for step_id, title, shot_cmd in STEPS:
            argv = [self.python, "-m", "tools.capstone_rehearse",
                    "--stdout", "--step", step_id]
            proc = subprocess.run(argv, capture_output=True, text=True,
                                  encoding="utf-8", cwd=self.root, timeout=120)
            output = (proc.stdout or proc.stderr or "").strip() or "(无输出)"
            command = " ".join('"%s"' % a if " " in a else a for a in argv)
            path, code, _err = self.emit(step_id, command, output, title, shot_cmd)
            paths.append(path)
            if code != 0:
                failures += 1
        return tuple(paths), failures
