#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Ch9 B5 下游无损回溯探针（AC-06/07，B5-3）。

只读调用既有 `verify_evidence.from_loot`（不改其判据 C1），断言登记簿
→ 证据载荷的 id/host/evidence/三件套一致；供测试与评审复现。
"""
import os
from typing import Any, Dict, List

from tools import verify_evidence as ve
from tools.loot_manage import registry as reg


def trace_from_loot(registry_path: str, evidence_dir: str = "") -> List[Dict[str, Any]]:
    """返回每条登记行的下游视图 {id, host, evidence, pieces}。"""
    root = evidence_dir or os.path.dirname(os.path.abspath(registry_path))
    payload = ve.from_loot(registry_path, evidence_dir=root)
    out = []
    for frag in payload.get("fragments", []):
        out.append({
            "id": frag.get("step_id", ""),
            "host": frag.get("host", ""),
            "evidence": frag.get("screenshot", ""),
            "pieces": dict(frag.get("pieces", {})),
        })
    return out


def lossless(registry_text: str, traced: List[Dict[str, Any]]) -> bool:
    """登记簿 id/host/evidence 与下游视图逐行一致且三件套齐全。"""
    rows = reg.parse_registry(registry_text).rows
    if len(rows) != len(traced):
        return False
    for row, view in zip(rows, traced):
        if row.id != view["id"] or row.host != view["host"]:
            return False
        if row.evidence != view["evidence"]:
            return False
        if not all(view["pieces"].get(k) for k in ("command", "output", "screenshot")):
            return False
    return True
