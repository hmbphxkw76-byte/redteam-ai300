#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""decoy-detect 命令行入口。

用法
  python tools/decoy_detect/cli.py run --inventory scan.json
  python tools/decoy_detect/cli.py run --inventory scan.json --out evidence/decoy/judgment.md \\
         --evidence-dir evidence/decoy --manifest evidence/decoy/manifest.jsonl

退出码：0 = 完成且质量门通过；1 = 质量门/证据违规；2 = 用法或输入错误。
"""
import argparse
import json
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(os.path.dirname(_HERE))
if __package__ in (None, ""):
    sys.path.insert(0, _ROOT)
    from tools.decoy_detect import model, runner
    from tools.decoy_detect.evidence import EvidenceWriter
else:
    from . import model, runner
    from .evidence import EvidenceWriter


def _build_parser():
    ap = argparse.ArgumentParser(
        prog="decoy-detect", description="诱饵机识别与判定（对齐 GOVERNANCE §5.3 时间盒纪律）")
    sub = ap.add_subparsers(dest="cmd")
    run = sub.add_parser("run", help="对一组主机记录执行三维度判定并落盘清单与证据")
    run.add_argument("--inventory", required=True, help="诱饵判定输入 JSON（含 hosts 列表）")
    run.add_argument("--out", default="-", help="判定清单 markdown 路径；'-' 写 stdout")
    run.add_argument("--evidence-dir", default="", help="证据片段目录（留空则不落证据）")
    run.add_argument("--manifest", default="", help="证据清单 JSONL 路径")
    run.add_argument("--timebox", type=int, default=1800, help="单台时间盒（秒，默认 1800=30min）")
    run.add_argument("--strict-evidence", action="store_true",
                     help="证据三件套不全即失败（配合 --evidence-dir）")
    run.add_argument("--json", action="store_true", help="以 JSON 打印运行摘要")
    return ap


def _screenshot_map(scan):
    """主机ID → 截图路径（来自输入记录的可选 screenshot 字段）。"""
    out = {}
    for host in scan.hosts:
        if isinstance(host, dict):
            shot = host.get("screenshot")
            if shot:
                out[str(host.get("host_id") or host.get("target") or "unknown")] = shot
    return out


def _emit_evidence(report, inventory_path, scan, evidence_dir, manifest):
    """对每个判定条目落一份证据片段；返回 (路径列表, 是否全部三件套)。"""
    writer = EvidenceWriter(evidence_dir, manifest=manifest)
    shots = _screenshot_map(scan)
    paths, all_complete = [], True
    for index, judgment in enumerate(report.judgments, 1):
        step = "decoy-%02d" % index
        command = "python tools/decoy_detect/cli.py run --inventory %s" % inventory_path
        output = ("host=%s\nhits=%s\nconclusion=%s\nreason=%s"
                  % (judgment.host_id, "、".join(judgment.dimension_values()),
                     judgment.conclusion.value, judgment.abandonment_reason))
        shot = shots.get(judgment.host_id, "")
        strict = bool(shot) and os.path.isfile(shot)
        path, code, _err = writer.emit(
            step, command, output, target=judgment.host_id,
            title="诱饵判定：%s" % judgment.host_id, screenshot=shot,
            shot_kind="transcript" if shot else "", strict=strict)
        paths.append(path)
        if code != 0:
            all_complete = False
    return writer, paths, all_complete


def _print_summary(report, as_json=False):
    if as_json:
        print(json.dumps(report.to_dict(), ensure_ascii=False, indent=2))
        return
    print("判定条目 %d（诱饵 %d / 不确定-已放弃 %d）　计分目标 %d　预期诱饵 ≈%d"
          % (len(report.judgments), report.decoy_count, report.uncertain_count,
             report.scored_count, report.expected_decoys))
    for j in report.judgments:
        print("  - %-16s %-10s %s" % (
            j.host_id, j.conclusion.value, "、".join(j.dimension_values())))
    if report.violations:
        print("质量门违规：")
        for item in report.violations:
            print("  - %s" % item)


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv:
        _build_parser().print_help()
        return 2
    if argv[0] in ("-h", "--help"):
        _build_parser().print_help()
        return 0
    if argv[0] != "run":
        argv = ["run"] + argv
    args = _build_parser().parse_args(argv)

    try:
        scan = model.load_scan(args.inventory)
    except ValueError as exc:
        print("ERROR: %s" % exc, file=sys.stderr)
        return 2

    report = runner.run_scan(scan, timebox_limit_seconds=args.timebox)

    if args.out == "-":
        sys.stdout.write(report.markdown)
    else:
        out_dir = os.path.dirname(os.path.abspath(args.out))
        if out_dir and not os.path.isdir(out_dir):
            os.makedirs(out_dir, exist_ok=True)
        with open(args.out, "w", encoding="utf-8") as handle:
            handle.write(report.markdown)

    evidence_failed = False
    if args.evidence_dir:
        _writer, paths, all_complete = _emit_evidence(
            report, args.inventory, scan, args.evidence_dir, args.manifest)
        evidence_failed = args.strict_evidence and not all_complete
        if not args.json:
            print("证据片段：%d 份 → %s" % (len(paths), args.evidence_dir))

    _print_summary(report, as_json=args.json)

    if not report.passed or evidence_failed:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
