#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Ch9 B5：云凭据指纹登记（AC-01..07）。

复用既有 `registry` 的 8 列 schema 与 append_row；只接收指纹三元组，
不接收明文凭据（P-2）。框架组合取矩阵 ⑧（无攻击框架）。
"""
import re
from typing import Any, Dict, Tuple

from . import registry as reg


def fingerprint_text(prefix: str, length: int, location: str) -> str:
    """构造 content 的脱敏表示：前缀…(len=N) @ 位置。"""
    return "%s…(len=%d) @ %s" % (prefix, int(length), location)


def next_id(text: str) -> str:
    """分配下一个不重复的 L-<n> 编号。"""
    parsed = reg.parse_registry(text)
    used = {int(m.group(1)) for r in parsed.rows
            for m in [re.fullmatch(r"L-(\d+)", r.id or "")] if m}
    n = max(used) + 1 if used else 1
    return "L-%d" % n


def register_cloud_fingerprint(text: str, prefix: str, length: int,
                               location: str, host: str, evidence: str,
                               timestamp: str = "") -> Tuple[str, Dict[str, Any]]:
    """追加一条云凭据指纹登记行。

    返回 (new_text, result)；result.ok=False 时不修改 text。
    """
    if not prefix or not location or not isinstance(length, int) or length < 1:
        return text, {"ok": False, "reason": "incomplete_fingerprint"}
    if not host or host == reg.DASH:
        return text, {"ok": False, "reason": "no_source_host"}
    content = fingerprint_text(prefix, length, location)
    # P-2：拒绝看似明文的输入（长度过长或含分隔结构）
    if len(prefix) > 8 or any(c in prefix for c in ":=@/"):
        return text, {"ok": False, "reason": "plaintext_rejected"}
    row = reg.LootRow(id=next_id(text), type="凭据", content=content,
                      host=host, evidence=evidence, timestamp=timestamp,
                      status=reg.DEFAULT_STATUS["凭据"], dual=reg.DASH)
    new_text = reg.append_row(text, row)
    check = reg.validate(reg.parse_registry(new_text), require_loot=False)
    # 登记助手只保证自身可控的结构检查（列/行/类型/状态/编号/主机/双通道）。
    # evidence 文件存在性与攻击路径小节由 loot-04 索引核对与 verify-evidence 承担，
    # 不在单行登记时判定（避免依赖调用方文件系统状态）。
    structural = ("columns", "rows", "types", "statuses", "ids", "hosts", "dual_channel")
    ok = all(check["checks"].get(k) for k in structural)
    return new_text, {"ok": ok, "id": row.id,
                      "content": content, "checks": check["checks"]}
