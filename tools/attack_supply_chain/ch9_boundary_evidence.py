#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""B6 strict 证据 emitter（AC-06/07）。

唯一出口 `tools/collect_evidence.py`（B6-4）；只组装 argv 经注入命令执行，
不自建证据实现（C1）。
"""
import os
from typing import Any, List

from .ch9_boundary_model import BoundaryVerdict

TOOL_REL = os.path.join("tools", "collect_evidence.py")


def build_evidence_argv(verdict: BoundaryVerdict, out_dir: str = ".",
                        target: str = "") -> List[str]:
    """组装 collect_evidence.py --strict 参数（可 copy/paste，无 shell）。"""
    argv = [
        "python", TOOL_REL,
        "--step", verdict.step_id,
        "--cmd", verdict.command,
        "--output", verdict.output,
        "--shot-cmd", verdict.shot_cmd,
        "--out", os.path.join(out_dir, "%s.md" % verdict.step_id),
        "--strict",
    ]
    if target:
        argv += ["--target", target]
    if verdict.transfer_to:
        argv += ["--note", "transfer_to:%s" % verdict.transfer_to]
    return argv


def emit_strict_evidence(ctx: Any, verdict: BoundaryVerdict) -> BoundaryVerdict:
    """发射 strict 证据；失败只标记 evidence_ok=False（不抛异常）。"""
    argv = build_evidence_argv(
        verdict, out_dir=getattr(ctx, "out_dir", "."),
        target=getattr(ctx, "target", ""))
    result = ctx.command.run(tuple(argv), timeout=getattr(ctx, "timeout", 60))
    # frozen dataclass：路由字段不可变，证据附着字段用 object.__setattr__ 写入。
    object.__setattr__(verdict, "evidence_path",
                       os.path.join(getattr(ctx, "out_dir", "."),
                                    "%s.md" % verdict.step_id))
    object.__setattr__(verdict, "evidence_ok", bool(result.ok))
    verdict.evidence_extra.update({"argv": list(argv), "exit_code": result.code})
    if not result.ok:
        verdict.evidence_extra["evidence_error"] = (
            result.stderr or result.stdout or "strict evidence failed")[:400]
    return verdict
