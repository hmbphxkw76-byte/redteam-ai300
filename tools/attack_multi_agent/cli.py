#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""attack-multi-agent 薄壳命令行（唯一入口的 CLI 适配，不含业务逻辑）。

用法示例：
  python -m tools.attack_multi_agent.cli http://BUS --paths A,B,C --flag "$FLAG"
  python -m tools.attack_multi_agent.cli http://BUS --step a2a-01 --json
"""
import argparse
import json

from .model import AttackRequest
from .runner import Runtime, run_attack

MODES = ("a2a-bus", "a2a-memory", "a2a-orchestrator", "agent-sse")


def build_parser():
    p = argparse.ArgumentParser(
        prog="attack-multi-agent",
        description="多智能体/A2A 操纵执行体（每步落盘三件套证据）")
    p.add_argument("target", help="消息总线/记忆存储/编排器基址")
    p.add_argument("--mode", default="a2a-bus", choices=MODES)
    p.add_argument("--paths", default="A,B,C", help="逗号分隔：A/B/C（三攻击面）")
    p.add_argument("--step", default="", help="单步复现，如 a2a-03")
    p.add_argument("--evidence-dir", default="", help="证据输出目录（默认 evidence/attack-multi-agent）")
    p.add_argument("--flag", default="", help="实测 ai_vector.txt 值（面板校验预言机等价双通道）")
    p.add_argument("--pyrit", action="store_true", help="开启 PyRIT HTTPTarget 深度补位")
    p.add_argument("--no-emit", action="store_true", help="不落盘证据（仅观测）")
    p.add_argument("--no-shot", action="store_true", help="不截图（证据标待补录）")
    p.add_argument("--json", action="store_true", help="输出完整 JSON 报告")
    return p


def main(argv=None):
    args = build_parser().parse_args(argv)
    paths = tuple(s for s in args.paths.split(",") if s)
    req = AttackRequest(
        target=args.target, mode=args.mode, paths=paths, step=args.step,
        evidence_dir=args.evidence_dir, emit=not args.no_emit,
        use_pyrit=args.pyrit, flag_value=args.flag)
    runtime = Runtime(shot_enabled=not args.no_shot)
    report = run_attack(req, runtime)
    if args.json:
        print(json.dumps(report.as_dict(), ensure_ascii=False, indent=2))
    else:
        for v in report.verdicts:
            print("%s | %s | %s" % (v.step_id, v.level, v.reason))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
