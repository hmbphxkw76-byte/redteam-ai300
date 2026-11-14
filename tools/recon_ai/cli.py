#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""recon-ai 命令行入口。

用法
  py tools/recon_ai/cli.py run --target http://192.168.40.189 --profile passive
  py tools/recon_ai/cli.py run --target http://192.168.40.189 --no-shots
  py tools/recon_ai/cli.py inventory --path evidence/recon-ai/ai-assets.json

退出码：0 = 完成且清单契约合规；1 = 完成但清单契约不合规；2 = 用法/参数错误。
单步骤失败属失败隔离（记 failed_steps），不影响退出码（AC-22）。
"""
import argparse
import json
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(os.path.dirname(_HERE))
if __package__ in (None, ""):
    sys.path.insert(0, _ROOT)
    from tools.recon_ai import policy, runner
else:
    from . import policy, runner


def _build_parser():
    ap = argparse.ArgumentParser(
        prog="recon-ai", description="AI 资产侦察与枚举（对齐 GOVERNANCE §6 证据基线）")
    sub = ap.add_subparsers(dest="cmd")

    run = sub.add_parser("run", help="对目标执行 7 步枚举并落盘证据与资产清单")
    run.add_argument("--target", required=True, help="目标入口，如 http://192.168.40.189")
    run.add_argument("--profile", default="passive", choices=policy.PROFILES,
                     help="执行分级：passive（默认，被动）/ active（追加定向端口探测）")
    run.add_argument("--lab", default="MM_04", help="实验面标识（用于 chat 端点模板）")
    run.add_argument("--out-dir", default="", help="产物目录（默认 evidence/recon-ai）")
    run.add_argument("--manifest", default="", help="证据清单 JSONL 路径")
    run.add_argument("--no-shots", action="store_true", help="不截图（证据标注待补录）")
    run.add_argument("--timeout", type=int, default=120, help="单请求超时（秒）")
    run.add_argument("--json", action="store_true", help="以 JSON 打印运行摘要")

    inv = sub.add_parser("inventory", help="读取并打印已有资产清单摘要")
    inv.add_argument("--path", required=True, help="ai-assets.json 路径")
    return ap


def _print_summary(report, as_json=False):
    inventory = report.inventory
    if as_json:
        print(json.dumps({
            "target": report.target, "profile": report.profile,
            "assets": len(inventory.assets),
            "undetermined": inventory.undetermined,
            "decoy_suspected": inventory.decoy_suspected,
            "failed_steps": report.failed_steps,
            "contract_violations": inventory.contract_violations(),
            "evidence": report.evidence_paths,
            "inventory_md": report.inventory_md,
            "manifest": report.manifest,
        }, ensure_ascii=False, indent=2))
        return
    print("目标：%s　分级：%s" % (report.target, report.profile))
    print("传输：%s　截图：%s　证据工具：%s"
          % (report.transport, report.shot, report.evidence_tool))
    print("-" * 92)
    print("%-10s %-8s %-30s %-18s %s" % ("步骤", "存在性", "产品/引擎", "截图", "证据片段"))
    fragment_of = {os.path.basename(p)[:-3]: p for p in report.evidence_paths}
    for spec in sorted(report.judgements):
        judgement = report.judgements[spec]
        print("%-10s %-8s %-30s %-18s %s" % (
            spec, judgement.existence.value, (judgement.product or "不可判定")[:28],
            os.path.basename(report.shots.get(spec, "")) or "待补录",
            os.path.basename(fragment_of.get(spec, "")) or "（未产出）"))
    print("-" * 92)
    print("资产 %d 条　不可判定 %d 类　疑似诱饵：%s"
          % (len(report.inventory.assets), len(report.inventory.undetermined),
             "是" if report.inventory.decoy_suspected else "否"))
    if report.failed_steps:
        print("失败步骤（已隔离）：%s" % "、".join(report.failed_steps))
    violations = report.inventory.contract_violations()
    if violations:
        print("契约违规：")
        for item in violations:
            print("  - %s" % item)
    if report.quality_failures:
        print("质量门失败（违反 C8，不得提交）：")
        for item in report.quality_failures:
            print("  - %s" % item)
    print("产物：%s　%s　%s" % (report.inventory_md, report.inventory_json, report.report_md))


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv or argv[0] not in ("run", "inventory", "-h", "--help"):
        argv = ["run"] + argv
    args = _build_parser().parse_args(argv)

    if args.cmd == "inventory":
        try:
            with open(args.path, encoding="utf-8") as f:
                data = json.load(f)
        except (OSError, ValueError) as exc:
            print("ERROR: 无法读取清单：%s" % exc, file=sys.stderr)
            return 2
        print("目标：%s　分级：%s　资产：%d"
              % (data.get("target"), data.get("profile"), len(data.get("assets", []))))
        for asset in data.get("assets", []):
            print("  %-28s %-10s %-28s %s" % (
                asset.get("asset_id"), asset.get("category"),
                asset.get("product"), asset.get("endpoint")))
        return 0

    try:
        profile = policy.normalize_profile(args.profile)
    except ValueError as exc:
        print("ERROR: %s" % exc, file=sys.stderr)
        return 2

    try:
        report = runner.run_recon(
            target=args.target, profile=profile, lab=args.lab,
            out_dir=args.out_dir or None,
            capture_shots=not args.no_shots,
            manifest=args.manifest or None,
            timeout=args.timeout,
        )
    except ValueError as exc:
        print("ERROR: %s" % exc, file=sys.stderr)
        return 2

    _print_summary(report, as_json=args.json)
    failed = bool(report.inventory.contract_violations() or report.quality_failures)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
