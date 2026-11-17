#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""证据落盘 seam（S2）：跨包共享公共 seam，委托共享收集器，不重实现格式。

【公共 seam 职责声明（C1 单一事实源）】
本模块虽物理位于 `tools/recon_ai/` 包内，但其 `EvidenceWriter` / `load_manifest`
是**仓库级共享证据适配层**，由以下技能跨包直接复用（保持原 import 路径，不迁移）：
  - `tools/attack_mcp_tool/evidence.py`
  - `tools/attack_embeddings/evidence.py`
  - `tools/attack_rag/evidence.py`
  - `tools/attack_multi_agent/evidence.py`
消费者清单以 `docs/contracts/consumers.md` 为准；格式唯一事实源为
`tools/collect_evidence.py`。修改本模块须按共享文件对待：影响上述 4 个技能，
须同步契约清单 CHANGELOG 并经 checkout_lock 门禁（ADR-0006）。
物理位置刻意保留在 recon_ai 包内，不新建公共包，避免 import 路径变更扩散。
"""
import os
import subprocess
import sys
from typing import Tuple

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DEFAULT_TOOL = os.path.join(ROOT, "tools", "collect_evidence.py")
from tools._evidence_contract import EvidenceWriterContract  # noqa: E402


class EvidenceWriter(EvidenceWriterContract):
    """证据写入器：子进程调用共享收集器（保证行为与 CLI 完全一致）。

    契约：符合 `tools/_evidence_contract.py#EvidenceWriterContract` 最小接口
    （describe / fragment_path / emit），由 scripts/check_evidence_contract.py 校验。
    本类为跨包共享公共 seam，签名与关键字别名保持不变。
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

    def fragment_path(self, step_id: str) -> str:
        return os.path.join(self.out_dir, "%s.md" % step_id)

    def emit(self, step_id: str, command: str, output: str = "",
             target="", title="",
             screenshot="", shot_kind="", shot_cmd="", profile="",
             script="", script_src="", script_note="", strict=True,
             note="", ai_log="", flag_panel="", flag_shot="") -> Tuple[str, int, str]:
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
        # flag 双通道（§6.2）：共享工具已支持 --flag-panel/--flag-shot，
        # 此处补齐透传，供 attack-mcp-tool 等下游技能复用同一适配层（C1）。
        if flag_panel:
            cmd += ["--flag-panel", flag_panel]
        if flag_shot:
            cmd += ["--flag-shot", flag_shot]
        if self.manifest:
            cmd += ["--manifest", self.manifest]
        if strict:
            cmd += ["--strict"]
        # Windows 子进程默认走 GBK：显式 UTF-8 两侧一致，非法字节以替换符降级，
        # 避免父进程 UnicodeDecodeError 丢掉整份证据（0xce 事故根因）。
        env = dict(os.environ)
        env["PYTHONUTF8"] = "1"
        env["PYTHONIOENCODING"] = "utf-8"
        # 一次性子进程异常（NTSTATUS/负退出码且 stderr 为空）重试一次；
        # 质量门失败（有 stderr）不重试，避免掩盖真实判定问题。
        for attempt in range(2):
            proc = subprocess.run(cmd, input=output or "", capture_output=True,
                                  text=True, encoding="utf-8", errors="replace",
                                  env=env, timeout=self.timeout)
            stderr = (proc.stderr or "").strip()
            if not _abnormal_exit(proc.returncode) or stderr or attempt == 1:
                break
        return out, proc.returncode, stderr


def _abnormal_exit(code):
    return code is not None and (code < 0 or 0xC0000000 <= code <= 0xFFFFFFFF)


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
