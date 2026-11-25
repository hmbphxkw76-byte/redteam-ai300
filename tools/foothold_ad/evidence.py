#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""证据参数组装（唯一出口为仓库 `tools/collect_evidence.py`）。

本模块不自建证据实现（C1），只把 `StepResult` 折叠为可 copy/paste 的 strict
参数列表；实际落盘由操作员执行，缺失 `--output-file` 时 `--strict` 必退出 1，
因此命令模板保留占位符而不伪造回显。
"""
import os
from typing import List, Optional

from .model import STEP_TITLES, StepResult

TOOL_REL = os.path.join("tools", "collect_evidence.py")

STEP_COMMANDS = {
    "ad-01": "ldapsearch -H ldap://<DC> -x -s base -b \"\" defaultNamingContext; nltest /domain_trusts /all_trusts /v",
    "ad-02": "python -m tools.foothold_ad.cli analyze --artifacts <ARTIFACT_DIR> --steps ad-02",
    "ad-03": "impacket-GetUserSPNs <DOMAIN>/<USER>:<PASS> -dc-ip <DC> -request -outputfile loot/kerb.txt",
    "ad-04": "certipy find -u <USER>@<DOMAIN> -p <PASS> -dc-ip <DC> -json -output loot/certipy",
    "ad-05": "python -m tools.foothold_ad.cli analyze --artifacts <ARTIFACT_DIR> --steps ad-05",
    "ad-06": "python -m tools.foothold_ad.cli analyze --artifacts <ARTIFACT_DIR> --steps ad-06",
    "ad-07": "whoami; id; type C:\\proof.txt",
    "ad-08": "python -m tools.foothold_ad.cli analyze --artifacts <ARTIFACT_DIR> --steps ad-08",
}


def summary(result: StepResult) -> str:
    """一行结论，供 `--output` 内联注入；只含判据与计数，不含明文凭据。"""
    parts = ["%s %s" % (result.step_id, result.verdict)]
    if result.findings:
        parts.append("findings=%d" % len(result.findings))
    if result.notes:
        parts.append("notes=%d" % len(result.notes))
    return " · ".join(parts)


def build_evidence_argv(result: StepResult, out_dir: str = "loot", target: str = "",
                        flag_panel: Optional[str] = None,
                        flag_shot: Optional[str] = None) -> List[str]:
    """组装 `collect_evidence.py --strict` 参数；ad-07 追加双通道标志。"""
    command = result.command or STEP_COMMANDS[result.step_id]
    out_path = os.path.join(out_dir, "%s.md" % result.step_id)
    argv = [
        "python", TOOL_REL,
        "--step", result.step_id,
        "--cmd", command,
        "--output", summary(result),
        "--shot-cmd", "screenshot --region %s" % result.step_id,
        "--out", out_path,
        "--strict",
        "--title", "%s %s" % (result.step_id, STEP_TITLES[result.step_id]),
    ]
    if target:
        argv += ["--target", target]
    if result.notes:
        argv += ["--note", " | ".join(result.notes)]
    if flag_panel is not None:
        argv += ["--flag-panel", flag_panel]
    if flag_shot is not None:
        argv += ["--flag-shot", flag_shot]
    return argv
