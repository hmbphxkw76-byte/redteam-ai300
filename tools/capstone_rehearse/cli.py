#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""CLI 三态：0=PASS / 1=质量门未过 / 2=用法错误（v2 AC-19）。

用法示例（技术读者可 copy/paste 复现）：
  python -m tools.capstone_rehearse --stdout
  python -m tools.capstone_rehearse --out result.json --report report.md
  python -m tools.capstone_rehearse --emit-evidence evidence/capstone-rehearse-drill
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Dict, Optional, Sequence

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from tools.capstone_rehearse.clock import FixedClock  # noqa: E402
from tools.capstone_rehearse.evidence import STEPS, EvidenceWriter  # noqa: E402
from tools.capstone_rehearse.inventory import RepoStageInventory  # noqa: E402
from tools.capstone_rehearse.report import render_report, render_summary  # noqa: E402
from tools.capstone_rehearse.walk import rehearse  # noqa: E402

STEP_IDS = tuple(s[0] for s in STEPS)


def _load_json(path: str) -> Dict:
    with open(path, "r", encoding="utf-8") as handle:
        value = json.load(handle)
    if not isinstance(value, dict):
        raise ValueError("JSON 顶层须为对象：%s" % path)
    return value


def _step_summary(step_id: str, result) -> str:
    if step_id == "cr-01":
        return "cr-01 覆盖度矩阵: %d 行, 就绪 %d, 证据链贯通 %d" % (
            len(result.matrix), sum(r.ready for r in result.matrix),
            sum(r.evidence_chain for r in result.matrix))
    if step_id == "cr-02":
        return "cr-02 24h 时间线: %d 段, 累计 %.1fh, 超时=%s" % (
            len(result.timeline) - 1,
            sum(s.duration for s in result.timeline[:-1]), result.overtime)
    if step_id == "cr-03":
        return "cr-03 缺口: 阻断 %d, 非阻断 %d" % (
            len(result.blocking), len(result.non_blocking))
    if step_id == "cr-04":
        return "cr-04 证据链贯通: %d/%d 阶段" % (
            sum(r.evidence_chain for r in result.matrix), len(result.matrix))
    if step_id == "cr-05":
        return "cr-05 演练报告: 四件产出齐全, ready_for_exam=%s" % result.ready_for_exam
    return "cr-06 机读结果: schema=%s, pending=%d, 退出码=%d" % (
        result.schema_version, len(result.pending),
        0 if result.ready_for_exam else 1)


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description="capstone-rehearse 考前演练走查")
    ap.add_argument("--out", help="机读 JSON 输出路径")
    ap.add_argument("--report", help="演练报告 markdown 输出路径")
    ap.add_argument("--measured", help="实测耗时 JSON 路径（关闭 VG-2 取证缺口）")
    ap.add_argument("--closed-gates", default="", help="逗号分隔的已关闭核实闸，如 VG-2,VG-3")
    ap.add_argument("--evidence-dir", help="演练证据片段目录（复用既有片段解析器，只读）")
    ap.add_argument("--emit-evidence", help="生成 cr-01…cr-06 证据片段到该目录")
    ap.add_argument("--step", choices=STEP_IDS, help="只输出单步摘要（供证据片段复现）")
    ap.add_argument("--stdout", action="store_true", help="把机读 JSON 打印到 stdout")
    return ap


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        measured = _load_json(args.measured) if args.measured else None
        closed = [x.strip() for x in args.closed_gates.split(",") if x.strip()]
        evidence_source = None
        if args.evidence_dir:
            if not os.path.isdir(args.evidence_dir):
                raise ValueError("证据片段目录不存在：%s" % args.evidence_dir)
            from report_exam.index import DirEvidenceSource
            evidence_source = DirEvidenceSource([args.evidence_dir], real_only=False)
        result = rehearse(RepoStageInventory(ROOT), FixedClock(measured=measured),
                          evidence_source=evidence_source, closed_gates=closed)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print("ERROR: %s" % exc, file=sys.stderr)
        return 2

    if args.step:
        print(_step_summary(args.step, result))
        return 0 if result.ready_for_exam else 1

    payload = json.dumps(result.to_dict(), ensure_ascii=False, indent=2, sort_keys=True)
    if args.stdout:
        print(payload)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as handle:
            handle.write(payload + "\n")
    if args.report:
        paths = []
        if args.evidence_dir:
            import glob
            paths = sorted(glob.glob(os.path.join(args.evidence_dir, "*.md")))
        with open(args.report, "w", encoding="utf-8") as handle:
            handle.write(render_report(result, paths))
    if args.emit_evidence:
        writer = EvidenceWriter(args.emit_evidence)
        paths, failures = writer.emit_all()
        if failures:
            print("ERROR: %d 份证据片段未过 --strict" % failures, file=sys.stderr)
            return 1
        print("证据片段：%d 份 → %s" % (len(paths), args.emit_evidence))
    if not (args.stdout or args.out or args.report or args.emit_evidence):
        print(render_summary(result))
    return 0 if result.ready_for_exam else 1


if __name__ == "__main__":
    raise SystemExit(main())
