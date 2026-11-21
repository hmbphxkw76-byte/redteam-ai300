#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""沙箱逃逸判据（mcp-09）：路径前缀碰撞 + symlink 跟随。

对齐 Ch7 §7.3 与 CVE-2025-53109（symlink）/ CVE-2025-53110（前缀碰撞）。
纯判据层：文件系统经 `fs` 注入（默认 os.path/realpath），单测可用假 FS 离线。
本模块只判定"缺陷是否存在"并产出可复现路径，不做真实越权写盘。

修复口径（调研 U-6）：规范路径 + 分隔符边界（防前缀碰撞）+
realpath 解析后二次校验（防 symlink 逃逸）。
"""
import json
import os
import posixpath
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

# 穿越载荷：允许目录 + ../ 逃逸到兄弟目录
TRAVERSAL_SUFFIX = "../.secrets/credentials.json"


def _norm(path: str) -> str:
    """统一 POSIX 语义规范化（Ch7/CVE 靶场为 Linux；避免 Windows 反斜杠漂移）。"""
    return posixpath.normpath(str(path).replace("\\", "/"))


@dataclass(frozen=True)
class EscapeResult:
    """一个逃逸判据的结果。"""

    kind: str            # prefix_bypass | symlink_escape | realpath_fix
    hit: bool            # 缺陷是否命中（或修复是否生效）
    input_path: str
    resolved: str = ""
    detail: str = ""

    def as_dict(self):
        return {"kind": self.kind, "hit": self.hit, "input_path": self.input_path,
                "resolved": self.resolved, "detail": self.detail}


def prefix_bypass(allowed: str, target: Optional[str] = None) -> EscapeResult:
    """判定"前缀检查早于规范化"缺陷：构造 allowed + ../ 路径。

    缺陷命中判据：naive `startswith(allowed)` 为真，但规范化后已越出 allowed。
    """
    target = target or posixpath.join(allowed, TRAVERSAL_SUFFIX)
    naive = target.startswith(allowed)
    normalized = _norm(target)
    inside_after_norm = normalized.startswith(_norm(allowed) + "/")
    hit = bool(naive and not inside_after_norm)
    return EscapeResult(
        kind="prefix_bypass", hit=hit, input_path=target, resolved=normalized,
        detail=("前缀检查命中但规范化后越界（CVE-2025-53110 类）" if hit
                else "规范化后仍在允许目录内，未命中前缀缺陷"))


def symlink_escape(allowed: str, link_name: str, outside_target: str,
                   fs: Optional[Any] = None) -> EscapeResult:
    """判定 symlink 逃逸：允许目录内软链指向目录外，逻辑规范在内、物理解析在外。"""
    fs = fs or os.path
    logical = _norm(posixpath.join(allowed, link_name))
    resolved = fs.realpath(logical)
    logical_inside = logical.startswith(_norm(allowed) + "/")
    physical_outside = not resolved.startswith(_norm(fs.realpath(allowed)) + "/")
    hit = bool(logical_inside and physical_outside)
    return EscapeResult(
        kind="symlink_escape", hit=hit, input_path=logical, resolved=resolved,
        detail=("逻辑路径在允许目录内但 realpath 指向目录外（CVE-2025-53109 类）"
                if hit else "realpath 后仍在允许目录内，未命中 symlink 逃逸"))


def realpath_fix_check(allowed: str, candidate: str, fs: Optional[Any] = None) -> EscapeResult:
    """修复对照：realpath 二次校验应拒绝越界路径。"""
    fs = fs or os.path
    resolved = fs.realpath(candidate)
    resolved = _norm(resolved)
    allowed_real = _norm(fs.realpath(allowed))
    inside = resolved.startswith(allowed_real + "/") or resolved == allowed_real
    return EscapeResult(
        kind="realpath_fix", hit=not inside, input_path=candidate, resolved=resolved,
        detail=("realpath 校验拒绝越界访问（修复生效）" if not inside
                else "realpath 校验放行（路径确在允许目录内）"))


def collect_results(results: List[EscapeResult]) -> Dict[str, Any]:
    """汇总为可序列化结构（含三判据，便于断言与报告渲染）。"""
    return {r.kind: r.as_dict() for r in results}


def _demo():
    """本地自证入口：渲染三判据结论（证据命令可 copy/paste 复现）。"""
    allowed = "/data/documents"
    out = collect_results([
        prefix_bypass(allowed),
        symlink_escape(allowed, "vendor-docs", "/data/secrets/prod.env"),
        realpath_fix_check(allowed, "/data/documents/../.secrets/credentials.json"),
    ])
    print(json.dumps(out, ensure_ascii=False, indent=1))
    return out


if __name__ == "__main__":
    _demo()
