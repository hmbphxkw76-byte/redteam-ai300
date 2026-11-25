#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""OSAI 八目标证据只读管线：核对目标映射、真实截图与 flag 双通道。

不写任何文件、不生成证据、不连接目标。判据来自：
- docs/operations/osai-target-map.md（唯一事实源）
- docs/contracts/collect_evidence.contract.md §1/§2（截图与双通道语义）
- tools/report_exam/index.py parse_fragment（下游解析契约）
"""
from __future__ import annotations

import argparse
import os
import re
import sys
from typing import Iterable, Tuple

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from tools.collect_evidence import _is_real_screenshot
from tools.report_exam.index import parse_fragment

PLACEHOLDER = "待考试窗口填写"
SCORED_TYPES = {"AI向量", "独立机", "传统向量", "域控"}


def read_targets(path: str) -> list[dict]:
    """解析目标映射 markdown 表；只认 `| T<数字> |` 行。"""
    targets = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line.startswith("| T") or line.startswith("| 目标ID"):
                continue
            cells = [c.strip() for c in line.strip("|").split("|")]
            if len(cells) < 8 or not cells[0][1:].isdigit():
                continue
            targets.append({
                "id": cells[0], "points": cells[1], "type": cells[2],
                "skill": cells[3], "fragment": cells[4], "flag": cells[5],
                "section": cells[6], "status": cells[7],
            })
    return targets


def _flag_dual_ok(text: str) -> bool:
    """从片段双通道明细表解析面板值与截图/正文值，二者非空且相等才算一致。"""
    panel = re.search(r"\|\s*控制面板提交值\s*\|\s*`?([^`|]+?)`?\s*\|", text)
    shot = re.search(r"\|\s*截图/正文中的值\s*\|\s*`?([^`|]+?)`?\s*\|", text)
    if not panel or not shot:
        return False
    a = panel.group(1).strip().replace("（缺失）", "")
    b = shot.group(1).strip().replace("（缺失）", "")
    return bool(a) and a == b


def _resolve(path: str, fragment_path: str, root: str) -> str:
    if not path or path.startswith(("http://", "https://")):
        return ""
    candidates = [path, os.path.join(os.path.dirname(fragment_path), path),
                  os.path.join(root, path)]
    for c in candidates:
        if os.path.isfile(c):
            return os.path.normpath(c)
    return os.path.normpath(candidates[-1])


def check_targets(target_map: str, fragments_dir: str, root: str) -> Tuple[bool, list[str]]:
    """返回 (ready, gaps)。gaps 为可直接执行的补件清单。"""
    gaps: list[str] = []
    targets = read_targets(target_map)
    if len(targets) != 8:
        gaps.append("目标映射表应有 8 行计分目标，实测 %d 行：%s" % (len(targets), target_map))
    total = 0
    for t in targets:
        total += int(t["points"]) if t["points"].isdigit() else 0
        if t["type"] not in SCORED_TYPES:
            gaps.append("%s: 未知类型 %s" % (t["id"], t["type"]))
        if t["fragment"] == PLACEHOLDER or not t["fragment"]:
            gaps.append("%s: 证据片段未登记（%s）" % (t["id"], t["fragment"] or "空"))
            continue
        frag_path = t["fragment"]
        for candidate in (frag_path, os.path.join(root, frag_path),
                          os.path.join(fragments_dir, os.path.basename(frag_path))):
            if os.path.isfile(candidate):
                frag_path = candidate
                break
        else:
            gaps.append("%s: 证据片段不存在：%s" % (t["id"], t["fragment"]))
            continue
        with open(frag_path, encoding="utf-8") as f:
            text = f.read()
        frag = parse_fragment(text, source_path=frag_path)
        shot = _resolve(frag.screenshot, frag_path, root)
        if not _is_real_screenshot(shot):
            gaps.append("%s: 真实截图缺失或无效：%s" % (t["id"], frag.screenshot or "片段未引用截图"))
        if not _flag_dual_ok(text) or t["flag"] not in ("已登记", "已提交一次"):
            gaps.append("%s: flag 双通道未登记（映射状态=%s，片段一致性未见）" % (t["id"], t["flag"]))
        if t["section"] == PLACEHOLDER or not t["section"]:
            gaps.append("%s: 报告小节未登记" % t["id"])
    if total != 100:
        gaps.append("计分目标分值合计应为 100，实测 %d" % total)
    return (not gaps), gaps


def main(argv: Iterable[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="OSAI 八目标证据只读校验（不生成证据）")
    ap.add_argument("--target-map", default="docs/operations/osai-target-map.md")
    ap.add_argument("--fragments-dir", default="evidence")
    ap.add_argument("--root", default=".")
    args = ap.parse_args(list(argv) if argv is not None else None)
    ready, gaps = check_targets(args.target_map, args.fragments_dir, args.root)
    if ready:
        print("八目标证据链：READY（仅代表本地证据齐备，正式考试事实仍须门户核验）")
        return 0
    print("八目标证据链：BLOCKED（%d 项缺口）" % len(gaps))
    for g in gaps:
        print("  - %s" % g)
    return 1


if __name__ == "__main__":
    sys.exit(main())
