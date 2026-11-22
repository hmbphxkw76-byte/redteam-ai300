#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Ch9 B5 六服务云凭据指纹登记（加固版）。

事实源 `docs/research/loot-manage-b5-hardening-canonical.md` B5-1..B5-6。
保持 `registry` 8 列 schema 与证据片段契约零漂移（P-4），明文禁落盘（P-1）。
保留公开函数与旧参数顺序，service 为可选追加参数。
"""
import re
from typing import Tuple

from . import registry as reg
from .ch9_b5_model import (
    GENERIC, SOURCES, CloudFingerprintVerdict,
)


def fingerprint_text(prefix: str, length: int, location: str,
                     service: str = GENERIC) -> str:
    """构造 content：服务:前缀…(len=N) @ 位置（服务标签为枚举字面，非明文）。"""
    return "%s:%s…(len=%d) @ %s" % (service, prefix, int(length), location)


def next_id(text: str) -> str:
    """分配下一个不重复的 L-<n> 编号。"""
    parsed = reg.parse_registry(text)
    used = {int(m.group(1)) for r in parsed.rows
            for m in [re.fullmatch(r"L-(\d+)", r.id or "")] if m}
    return "L-%d" % (max(used) + 1 if used else 1)


def _plaintext(prefix: str) -> bool:
    """P-1：裸/引号形态的明文判定（含 `:=@/` 或过长、带引号）。"""
    if not prefix or len(prefix) > 8:
        return True
    if any(c in prefix for c in ":=@/\"'"):
        return True
    return False


def register_cloud_fingerprint(text: str, prefix: str, length: int,
                               location: str, host: str, evidence: str,
                               service: str = GENERIC,
                               timestamp: str = "") -> CloudFingerprintVerdict:
    """追加一条六服务凭据指纹行；失败时 text 不变。

    保留旧调用签名（前 6 参数顺序不变），service 可选。
    """
    if service not in SOURCES:
        return CloudFingerprintVerdict(False, "unknown_service", service=service, text=text)
    if not prefix or not location or not isinstance(length, int) or length < 1:
        return CloudFingerprintVerdict(False, "incomplete_fingerprint", service=service, text=text)
    if _plaintext(prefix):
        return CloudFingerprintVerdict(False, "plaintext_rejected", service=service, text=text)
    if not host or host == reg.DASH:
        return CloudFingerprintVerdict(False, "no_source_host", service=service, text=text)
    if location not in SOURCES.values() and location != SOURCES[service]:
        # 允许上游注入的自定义位置锚点（R-1），仅拒绝空与非字符串。
        if not isinstance(location, str):
            return CloudFingerprintVerdict(False, "invalid_location", service=service, text=text)
    content = fingerprint_text(prefix, length, location, service)
    row = reg.LootRow(id=next_id(text), type="凭据", content=content,
                      host=host, evidence=evidence, timestamp=timestamp,
                      status=reg.DEFAULT_STATUS["凭据"], dual=reg.DASH)
    new_text = reg.append_row(text, row)
    check = reg.validate(reg.parse_registry(new_text), require_loot=False)
    structural = ("columns", "rows", "types", "statuses", "ids", "hosts", "dual_channel")
    ok = all(check["checks"].get(k) for k in structural)
    if not ok:
        return CloudFingerprintVerdict(False, "invalid_location", service=service, text=text)
    return CloudFingerprintVerdict(
        True, "", row.id, content, service, location, host, evidence,
        checks=dict(check["checks"]), text=new_text)
