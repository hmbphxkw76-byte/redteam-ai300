#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Ch9 strict 证据 emitter（AC-08/09）。

唯一出口为仓库 `tools/collect_evidence.py`（H-6）；本模块只组装参数列表，
经 ctx.command 注入执行，不自建证据实现（C1 单一事实源）。
"""
import os
from typing import Any, Dict, List

from .ch9_model import TriadVerdict

TOOL_REL = os.path.join("tools", "collect_evidence.py")


def build_evidence_argv(verdict: TriadVerdict, out_dir: str = ".",
                        target: str = "") -> List[str]:
    """组装 collect_evidence.py --strict 参数（可 copy/paste，AC-09）。"""
    out_path = os.path.join(out_dir, "%s.md" % verdict.step_id)
    argv = [
        "python", TOOL_REL,
        "--step", verdict.step_id,
        "--cmd", verdict.command,
        "--output", verdict.output,
        "--shot-cmd", verdict.shot_cmd,
        "--out", out_path,
        "--strict",
    ]
    if target:
        argv += ["--target", target]
    for fp in verdict.fingerprints:
        argv += ["--note", "fingerprint:%s" % fp.as_text()]
    return argv


def emit_strict_evidence(ctx: Any, verdict: TriadVerdict) -> TriadVerdict:
    """发射 strict 证据；失败只标记 evidence_ok=False（不抛异常，AC-08）。"""
    argv = build_evidence_argv(
        verdict, out_dir=getattr(ctx, "out_dir", "."),
        target=getattr(ctx, "target", ""))
    result = ctx.command.run(tuple(argv), timeout=getattr(ctx, "timeout", 60))
    verdict.evidence_path = os.path.join(getattr(ctx, "out_dir", "."),
                                         "%s.md" % verdict.step_id)
    verdict.evidence_ok = bool(result.ok)
    verdict.evidence_extra.update({
        "argv": list(argv),
        "exit_code": result.code,
    })
    if not result.ok:
        verdict.evidence_extra["evidence_error"] = (
            result.stderr or result.stdout or "strict evidence failed")[:400]
    return verdict
