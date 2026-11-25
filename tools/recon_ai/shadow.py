#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""影子端点离线发现（Ch2 §4.3「影子 API 端点」）。

做法：把「OpenAPI 声明路径」与「前端产物中出现的路径字面量」做差集，
产出未声明但被引用的候选端点。纯函数、零网络、零第三方；结果确定性排序。

边界（不改 recon-01..07 判据、不改七字段资产清单）：
- 只处理调用方已采集的本体（OpenAPI 文档、HTML/JS 文本），不发起请求；
- 仅作 recon-05「关键输出」的补充证据，不产出资产条目；
- 命中只说明「前端引用了未声明路径」，不等于该端点可用（可用性由 recon 探测判定）。
"""
import re
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Mapping, Sequence, Tuple

# 静态资源后缀：命中直接丢弃（不是 API 影子）。
STATIC_SUFFIXES = (
    ".js", ".mjs", ".css", ".map", ".png", ".jpg", ".jpeg", ".gif", ".svg",
    ".ico", ".woff", ".woff2", ".ttf", ".eot", ".webp", ".avif", ".txt",
)
# 路径字面量：引号或括号包裹、以 / 起始、至少两段。
PATH_RE = re.compile(r"""["'`(](\/[A-Za-z0-9_\-{}$:.@~%]+(?:\/[A-Za-z0-9_\-{}$:.@~%]+)+)["'`)]""")
NUMERIC_SEGMENT = re.compile(r"^(\d+|[0-9a-f]{8}-[0-9a-f-]{27,})$", re.I)
CROSS_ORIGIN = re.compile(r"^(https?:)?//", re.I)

HIGH = "high"
MEDIUM = "medium"


@dataclass(frozen=True)
class ShadowCandidate:
    path: str
    confidence: str
    references: int
    reason: str

    def to_dict(self) -> Dict[str, Any]:
        return {"path": self.path, "confidence": self.confidence,
                "references": self.references, "reason": self.reason}


def normalize_path(raw: str) -> str:
    """去查询串/锚点、折叠重复斜杠、去尾斜杠；数字与 GUID 段归一为 `{id}`。"""
    text = str(raw or "").strip().split("#", 1)[0].split("?", 1)[0]
    if not text.startswith("/"):
        return ""
    segments = [seg for seg in text.split("/") if seg]
    normalized = ["{id}" if NUMERIC_SEGMENT.match(seg) else seg for seg in segments]
    return "/" + "/".join(normalized) if normalized else ""


def _is_static(path: str) -> bool:
    low = path.lower()
    return low.endswith(STATIC_SUFFIXES)


def declared_paths(openapi: Any) -> Tuple[str, ...]:
    """从 OpenAPI 文档取声明路径；支持 `paths` 映射或路径列表。"""
    raw: Any = openapi
    if isinstance(openapi, Mapping):
        raw = openapi.get("paths")
    if isinstance(raw, Mapping):
        items = list(raw.keys())
    elif isinstance(raw, (list, tuple)):
        items = list(raw)
    else:
        items = []
    out = {normalize_path(str(item)) for item in items if str(item).strip()}
    return tuple(sorted(p for p in out if p))


def observed_paths(documents: Sequence[Mapping[str, Any]]) -> Tuple[str, ...]:
    """从 HTML/JS 文本中提取路径字面量；跨域与静态资源剔除。"""
    found: List[str] = []
    for doc in documents or ():
        text = str((doc or {}).get("text") or "")
        for match in PATH_RE.finditer(text):
            candidate = match.group(1)
            if CROSS_ORIGIN.match(candidate) or _is_static(candidate):
                continue
            normalized = normalize_path(candidate)
            if normalized:
                found.append(normalized)
    return tuple(found)


def shadow_candidates(declared: Iterable[str], observed: Iterable[str]) -> Tuple[ShadowCandidate, ...]:
    """差集并定级：含具体业务段（非 {id}）记 high，全为参数段记 medium。"""
    declared_set = {normalize_path(item) for item in declared if normalize_path(item)}
    counts: Dict[str, int] = {}
    for item in observed:
        path = normalize_path(item)
        if path and path not in declared_set:
            counts[path] = counts.get(path, 0) + 1

    results: List[ShadowCandidate] = []
    for path in sorted(counts):
        segments = [seg for seg in path.split("/") if seg]
        concrete = [seg for seg in segments if seg != "{id}"]
        confidence = HIGH if len(concrete) >= 2 else MEDIUM
        reason = ("前端引用未声明路径（%d 个具体段）" % len(concrete)) if confidence == HIGH \
            else "前端引用未声明路径（仅 1 个具体段，易与通用路由重名）"
        results.append(ShadowCandidate(path, confidence, counts[path], reason))
    return tuple(results)


def analyze(observation: Mapping[str, Any]) -> Dict[str, Any]:
    """消费一条 `kind=shadow` 观测：`{"openapi": {...}|[...], "documents": [{"name","text"}]}`。"""
    obs = observation if isinstance(observation, Mapping) else {}
    declared = declared_paths(obs.get("openapi"))
    observed = observed_paths(obs.get("documents") or ())
    candidates = shadow_candidates(declared, observed)
    if not observed:
        status = "UNDETERMINED"
    elif candidates:
        status = "PRESENT"
    else:
        status = "ABSENT"
    return {
        "status": status,
        "declared": list(declared),
        "observed": sorted(set(observed)),
        "candidates": [item.to_dict() for item in candidates],
        "basis": "声明路径与前端字面量差集；命中不等于端点可用（§2.3 Ch2 C8）",
    }
