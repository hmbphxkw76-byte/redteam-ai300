#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""recon-ai 命令行入口。

用法
  py tools/recon_ai/cli.py run --target http://<TARGET> --profile passive
  py tools/recon_ai/cli.py run --target http://<TARGET> --target-profile my-target --no-shots
  py tools/recon_ai/cli.py inventory --path evidence/recon-ai/ai-assets.json
  py tools/recon_ai/cli.py verify --run evidence/recon-ai/runs/<run_id>
  py tools/recon_ai/cli.py analyze --input observations.json --out ch2-analysis.json

退出码：0 = 完成且 C1–C9 门禁 PASS；1 = 完成但门禁 BLOCKED；
2 = 用法/参数错误。单步骤失败属失败隔离（记 failed_steps），
但会让对应门禁失败（不静默通过）。
"""
import argparse
import json
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(os.path.dirname(_HERE))
if __package__ in (None, ""):
    sys.path.insert(0, _ROOT)
    from tools.recon_ai import ch2, policy, runner, verifier
    from tools import target_profile as target_profile_mod
else:
    from . import ch2, policy, runner, verifier
    from tools import target_profile as target_profile_mod


def _build_parser():
    ap = argparse.ArgumentParser(
        prog="recon-ai", description="AI 资产侦察与枚举（对齐 GOVERNANCE §6 证据基线）")
    sub = ap.add_subparsers(dest="cmd")

    run = sub.add_parser("run", help="对目标执行 7 步枚举并落盘证据与资产清单")
    run.add_argument("--target", required=True, help="目标入口，如 http://<TARGET>")
    run.add_argument("--profile", default="passive", choices=policy.PROFILES,
                     help="执行分级：passive（默认，被动）/ active（追加定向端口探测）")
    run.add_argument("--lab", default="", help="chat 角色实验面标识（覆盖画像映射；缺省取画像）")
    run.add_argument("--target-profile", default=None,
                     help="目标画像名或 JSON 路径（默认读 REDTEAM_TARGET_PROFILE 环境变量，均无则 generic 全占位）")
    run.add_argument("--out-dir", default="", help="产物目录（默认 evidence/recon-ai）")
    run.add_argument("--manifest", default="", help="证据清单 JSONL 路径")
    run.add_argument("--no-shots", action="store_true", help="不截图（证据标注待补录）")
    run.add_argument("--timeout", type=int, default=120, help="单请求超时（秒）")
    run.add_argument("--json", action="store_true", help="以 JSON 打印运行摘要")

    inv = sub.add_parser("inventory", help="读取并打印已有资产清单摘要")
    inv.add_argument("--path", required=True, help="ai-assets.json 路径")

    verify = sub.add_parser("verify", help="对已有运行目录复算 C1–C9 门禁")
    verify.add_argument("--run", required=True, help="运行目录（含 run.json）")
    verify.add_argument("--json", action="store_true", help="以 JSON 打印门禁结果")

    analyze = sub.add_parser(
        "analyze", help="Ch2 对齐旁路分析（离线，零网络，不改 7 步门禁）")
    analyze.add_argument("--input", required=True,
                         help="观测 JSON 文件（含 observations 数组）")
    analyze.add_argument("--out", default="", help="分析 JSON 落盘路径；缺省仅打印摘要")
    return ap


def _print_summary(report, as_json=False):
    inventory = report.inventory
    verification = getattr(report, "verification", None)
    if as_json:
        payload = {
            "target": report.target, "profile": report.profile,
            "run_id": getattr(report, "run_id", ""),
            "run_dir": getattr(report, "run_dir", ""),
            "assets": len(inventory.assets),
            "undetermined": inventory.undetermined,
            "decoy_suspected": inventory.decoy_suspected,
            "failed_steps": report.failed_steps,
            "contract_violations": inventory.contract_violations(),
            "evidence": report.evidence_paths,
            "inventory_md": report.inventory_md,
            "manifest": report.manifest,
        }
        if verification is not None:
            payload["verdict"] = verification.verdict
            payload["failed_checks"] = [c.name for c in verification.failed()]
            payload["verification_json"] = getattr(report, "verification_json", "")
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return
    print("目标：%s　分级：%s　运行：%s"
          % (report.target, report.profile, getattr(report, "run_id", "-")))
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
    if verification is not None:
        print("自校验门禁（C1–C9）：%s" % verification.verdict)
        for check in verification.failed():
            print("  - FAIL %s：%s" % (check.name, check.detail))
    print("产物：%s　%s　%s" % (report.inventory_md, report.inventory_json, report.report_md))
    if getattr(report, "run_dir", ""):
        print("运行目录：%s" % report.run_dir)


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv or argv[0] not in ("run", "inventory", "verify", "analyze",
                                   "-h", "--help"):
        argv = ["run"] + argv
    args = _build_parser().parse_args(argv)

    if args.cmd == "verify":
        result = verifier.verify_run(args.run)
        if args.json:
            print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))
        else:
            print("运行：%s　目标：%s　判定：%s"
                  % (result.run_id or "-", result.target or "-", result.verdict))
            for check in result.checks:
                print("%s %-16s %s" % ("PASS" if check.ok else "FAIL",
                                       check.name, check.detail))
        return 0 if result.verdict == "PASS" else 1

    if args.cmd == "analyze":
        try:
            with open(args.input, encoding="utf-8") as f:
                observations = json.load(f)
        except (OSError, ValueError) as exc:
            print("ERROR: 无法读取观测文件：%s" % exc, file=sys.stderr)
            return 2
        result = ch2.analyze(observations)
        violations = ch2.validate_analysis(result)
        if args.out:
            try:
                with open(args.out, "w", encoding="utf-8") as f:
                    json.dump(result, f, ensure_ascii=False, indent=2)
            except OSError as exc:
                print("ERROR: 无法写入分析结果：%s" % exc, file=sys.stderr)
                return 2
        print("旁路分析：分层 %d 层，信号 %d 条，结论 %d 项，"
              "端点判定 %d 条，仓库工件 %d 类，校验违规 %d 项"
              % (len(result["taxonomy"]), len(result["signals"]),
                 len(result["findings"]), len(result["endpoints"]),
                 len(result["repository"]), len(violations)))
        for item in violations:
            print("  - 违规：%s" % item)
        if args.out:
            print("分析产物：%s" % args.out)
        return 1 if violations else 0

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
        target_obj = (target_profile_mod.resolve(args.target_profile)
                      if getattr(args, "target_profile", None)
                      else target_profile_mod.current())
        report = runner.run_recon(
            target=args.target, profile=profile, lab=args.lab,
            out_dir=args.out_dir or None,
            capture_shots=not args.no_shots,
            manifest=args.manifest or None,
            timeout=args.timeout,
            target_profile=target_obj,
        )
    except ValueError as exc:
        print("ERROR: %s" % exc, file=sys.stderr)
        return 2

    _print_summary(report, as_json=args.json)
    failed = bool(report.inventory.contract_violations() or report.quality_failures)
    verification = getattr(report, "verification", None)
    if verification is not None and verification.verdict != "PASS":
        failed = True
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
