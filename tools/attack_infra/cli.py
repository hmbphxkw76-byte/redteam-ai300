#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""attack-infra 命令行入口。

用法
  py tools/attack_infra/cli.py --target 192.168.40.189
  py tools/attack_infra/cli.py --target 192.168.40.189 --step infra-01 --step infra-03
  py tools/attack_infra/cli.py --target 192.168.40.189 --allow-inference
  py tools/attack_infra/cli.py --target 192.168.40.189 --dry-run

退出码：0 = 无阻断项；1 = 存在 BLOCKED 或证据门失败；2 = 用法/参数错误。
只读优先：写操作未实现（`--allow-write` 仅记录意图，见 AC-08）。
"""
import argparse
import json
import os
import shlex
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(os.path.dirname(_HERE))
if __package__ in (None, ""):
    sys.path.insert(0, _ROOT)
    from tools.attack_infra import fingerprint
    from tools.attack_infra import report as report_mod
    from tools.attack_infra import runner
    from tools.attack_infra.command import SubprocessCommand
    from tools.attack_infra.evidence import EvidenceWriter
    from tools.attack_infra.inventory import load_endpoints
    from tools.attack_infra.model import STEP_IDS, RunContext
    from tools.attack_infra.shot import ShotPlanner
    from tools.attack_infra.transport import UrllibTransport
else:
    from . import fingerprint
    from . import report as report_mod
    from . import runner
    from .command import SubprocessCommand
    from .evidence import EvidenceWriter
    from .inventory import load_endpoints
    from .model import STEP_IDS, RunContext
    from .shot import ShotPlanner
    from .transport import UrllibTransport


def _build_parser():
    ap = argparse.ArgumentParser(
        prog="attack-infra",
        description="AI 基础设施与部署利用（对齐 GOVERNANCE §6 证据基线）")
    ap.add_argument("--target", required=True, help="演练目标主机或 URL")
    ap.add_argument("--step", action="append", choices=list(STEP_IDS),
                    help="仅执行指定步骤（可重复）；缺省执行全部 8 步")
    ap.add_argument("--out-dir", default="loot", help="证据片段输出目录")
    ap.add_argument("--ports", default="", help="逗号分隔的端口候选（覆盖默认指纹端口）")
    ap.add_argument("--inventory", default="",
                    help="recon-ai 资产清单 JSON（复用其中的候选端点）")
    ap.add_argument("--secondary-target", action="append", default=[],
                    help="次要目标（独立机），可重复")
    ap.add_argument("--decoy-timebox", type=int, default=30,
                    help="诱饵机/低价值主机时间盒（分钟，缺省 30）")
    ap.add_argument("--bucket", action="append", default=[], help="待核云存储桶")
    ap.add_argument("--gateway-config", action="append", default=[],
                    help="待核推理网关配置文件")
    ap.add_argument("--exec-cmd", default="", help="infra-06 代码执行命令（参数列表）")
    ap.add_argument("--namespace", default="", help="infra-04 Kubernetes 命名空间")
    ap.add_argument("--service-account", default="", help="infra-04 服务账号名")
    ap.add_argument("--allow-inference", action="store_true",
                    help="允许单次推理调用（infra-03/07）")
    ap.add_argument("--allow-write", action="store_true",
                    help="允许写操作（当前仅记录意图，不实现）")
    ap.add_argument("--inference-model", default="", help="推理使用的模型名")
    ap.add_argument("--inference-prompt", default="Reply with exactly: PWNED")
    ap.add_argument("--inference-endpoint", default="", help="覆盖推理端点 URL")
    ap.add_argument("--flag-panel", default="", help="面板提交的 flag 值")
    ap.add_argument("--flag-shot", default="", help="截图中读取的 flag 值")
    ap.add_argument("--decoy", action="store_true", help="按疑似诱饵机提前终止")
    ap.add_argument("--timeout", type=int, default=30)
    ap.add_argument("--no-evidence", action="store_true", help="不落盘证据（仅调试）")
    ap.add_argument("--dry-run", action="store_true", help="只打印执行计划，不发请求")
    ap.add_argument("--json", action="store_true", help="以 JSON 输出报告")
    return ap


def build_context(args) -> RunContext:
    ports = tuple(int(p) for p in args.ports.split(",") if p.strip())
    exec_argv = tuple(shlex.split(args.exec_cmd)) if args.exec_cmd else ()
    fingerprint.normalize_target(args.target)  # 参数校验：空/非法 target → ValueError
    return RunContext(
        target=args.target,
        transport=UrllibTransport(timeout=args.timeout),
        command=SubprocessCommand(),
        evidence=None if args.no_evidence else EvidenceWriter(args.out_dir),
        shot=ShotPlanner(os.path.join(args.out_dir, "shots")),
        out_dir=args.out_dir,
        timeout=args.timeout,
        allow_inference=args.allow_inference,
        allow_write=args.allow_write,
        buckets=tuple(args.bucket),
        inventory_endpoints=load_endpoints(args.inventory),
        secondary_targets=tuple(args.secondary_target),
        decoy_timebox_minutes=args.decoy_timebox,
        gateway_configs=tuple(args.gateway_config),
        exec_argv=exec_argv,
        inference_prompt=args.inference_prompt,
        inference_model=args.inference_model,
        inference_endpoint=args.inference_endpoint,
        namespace=args.namespace,
        service_account=args.service_account,
        flag_panel=args.flag_panel,
        flag_shot=args.flag_shot,
        decoy=args.decoy,
        step_ids=tuple(args.step) if args.step else STEP_IDS,
        ports=ports or None,
    )


def main(argv=None) -> int:
    args = _build_parser().parse_args(argv)
    try:
        ctx = build_context(args)
    except ValueError as exc:
        print("ERROR: %s" % exc, file=sys.stderr)
        return 2
    if args.dry_run:
        print("执行计划（未发请求）：target=%s steps=%s"
              % (ctx.target, ",".join(ctx.step_ids)))
        if ctx.allow_write:
            print("注记：--allow-write 已置位，但写操作未实现（AC-08）")
        return 0
    runs = runner.run_targets(ctx)
    print(render_runs(runs, as_json=args.json))
    return max([report_mod.exit_code(run.report) for run in runs] or [0])


def render_runs(runs, as_json=False) -> str:
    """渲染多目标结果（主目标 + 独立机）；纯格式化，便于单测覆盖。"""
    if as_json:
        return json.dumps({
            "targets": [
                {"target": run.target, "role": run.role,
                 "report": report_mod.to_dict(run.report)}
                for run in runs
            ]
        }, ensure_ascii=False, indent=2)
    chunks = []
    for run in runs:
        chunks.append("### 目标 %s（%s）" % (run.target, run.role))
        chunks.append(report_mod.summary(run.report))
        chunks.append("")
        chunks.append(report_mod.render(run.report))
        chunks.append("")
    return "\n".join(chunks).rstrip()


if __name__ == "__main__":
    sys.exit(main())
