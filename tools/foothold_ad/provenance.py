#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""工件来源与完整性校验（provenance）。

离线模式下没有实时目标可复核，工件本身就是唯一事实来源，因此必须可追溯：
每条工件在 `artifact_manifest.json` 中登记 `sha256` / 采集工具与版本 / 采集时间 /
操作者。清单缺失或哈希不符即该工件**不可信**，不得作为证据提交
（`skills/foothold-ad/SKILL.md` 质量门）。
"""
import hashlib
import json
import os
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

MANIFEST_FILE = "artifact_manifest.json"
REQUIRED_FIELDS = ("sha256", "source", "tool_version", "captured_at", "operator")
DEFAULT_ARTIFACTS = ("directory.json", "templates.json", "trusts.json")
OPTIONAL_ARTIFACTS = ("tickets.json", "proof.json")


@dataclass(frozen=True)
class EntryCheck:
    file: str
    ok: bool
    problems: Tuple[str, ...] = ()

    def to_dict(self) -> Dict[str, Any]:
        return {"file": self.file, "ok": self.ok, "problems": list(self.problems)}


@dataclass
class VerifyReport:
    ok: bool = False
    manifest_found: bool = False
    entries: Tuple[EntryCheck, ...] = ()
    untrusted: Tuple[str, ...] = ()
    missing_files: Tuple[str, ...] = ()
    notes: Tuple[str, ...] = ()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ok": self.ok,
            "manifest_found": self.manifest_found,
            "entries": [e.to_dict() for e in self.entries],
            "untrusted": list(self.untrusted),
            "missing_files": list(self.missing_files),
            "notes": list(self.notes),
        }


def sha256_file(path: str, chunk: int = 1 << 20) -> str:
    """流式计算文件 sha256，避免整文件读入内存。"""
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        while True:
            block = handle.read(chunk)
            if not block:
                break
            digest.update(block)
    return digest.hexdigest()


def load_manifest(path: str) -> Dict[str, Mapping[str, Any]]:
    """读取清单并归一化为 {文件名: 条目}；支持 `artifacts` 数组或映射两种形态。"""
    with open(path, "r", encoding="utf-8") as handle:
        payload = json.load(handle)
    if isinstance(payload, Mapping) and "artifacts" in payload:
        raw: Any = payload.get("artifacts")
    else:
        raw = payload
    table: Dict[str, Mapping[str, Any]] = {}
    if isinstance(raw, Mapping):
        for name, entry in raw.items():
            if isinstance(entry, Mapping):
                table[str(name)] = entry
    elif isinstance(raw, (list, tuple)):
        for entry in raw:
            if isinstance(entry, Mapping) and entry.get("file"):
                table[str(entry["file"])] = entry
    if not table:
        raise ValueError("清单中无可解析条目: %s" % path)
    return table


def verify(artifacts_dir: str, files: Optional[Iterable[str]] = None) -> VerifyReport:
    """校验清单与实文件一致性；不可信文件列入 `untrusted`。

    `files` 缺省时校验「目录中实际存在的已知工件」∪「清单登记的条目」，
    使清单覆盖子集也成立；显式传入 `files` 时按并集严格校验。
    """
    manifest_path = os.path.join(artifacts_dir, MANIFEST_FILE)

    report = VerifyReport()
    existing = tuple(sorted(
        name for name in DEFAULT_ARTIFACTS + OPTIONAL_ARTIFACTS
        if os.path.isfile(os.path.join(artifacts_dir, name))))
    if not os.path.isfile(manifest_path):
        report.untrusted = existing if files is None else tuple(files)
        report.notes = ("缺少 %s，全部工件不可信" % MANIFEST_FILE,)
        return report

    report.manifest_found = True
    try:
        table = load_manifest(manifest_path)
    except (ValueError, json.JSONDecodeError) as exc:
        report.untrusted = existing if files is None else tuple(files)
        report.notes = ("清单不可解析: %s" % exc,)
        return report

    if files is None:
        targets: List[str] = sorted(set(existing) | set(table))
    else:
        targets = sorted(set(str(name) for name in files) | set(table))

    entries: List[EntryCheck] = []
    untrusted: List[str] = []
    missing: List[str] = []
    for name in targets:
        path = os.path.join(artifacts_dir, name)
        entry = table.get(name)
        problems: List[str] = []
        if not os.path.isfile(path):
            missing.append(name)
            problems.append("清单登记但文件缺失")
        elif entry is None:
            problems.append("文件未在清单登记")
        else:
            absent = [key for key in REQUIRED_FIELDS if not str(entry.get(key) or "").strip()]
            if absent:
                problems.append("清单字段缺失: %s" % ", ".join(absent))
            expected = str(entry.get("sha256") or "").strip().lower()
            actual = sha256_file(path)
            if expected and expected != actual:
                problems.append("sha256 不符（清单 %s… 实测 %s…）" % (expected[:8], actual[:8]))
        ok = not problems
        entries.append(EntryCheck(name, ok, tuple(problems)))
        if problems and name not in missing:
            untrusted.append(name)

    report.entries = tuple(entries)
    report.untrusted = tuple(untrusted)
    report.missing_files = tuple(missing)
    report.ok = not untrusted and not missing and bool(entries)
    return report
