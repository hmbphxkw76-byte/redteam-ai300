#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""端到端演示：以标准库假后端跑通 attack-ai-agent 全 12 步并落盘证据。

用法（技术读者可直接 copy/paste）：
  python tools/attack_ai_agent/demo.py
  python tools/attack_ai_agent/demo.py --step aia-02 --target 10.0.0.5
  python tools/attack_ai_agent/demo.py --scenario refusal
  python tools/attack_ai_agent/demo.py --no-memory --no-tools

真实端点模式需人工注入凭据与端点（triage 判为 ready-for-human），
本演示在 CI 中零外部依赖运行（ADR-0003）。
"""
import argparse
import os
import sys

if __package__ in (None, ""):
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(
        os.path.abspath(__file__)))))
    from tools.attack_ai_agent import run_attack
    from tools.attack_ai_agent.backends import FakePyRITBackend
else:
    from . import run_attack
    from .backends import FakePyRITBackend


def main(argv=None):
    ap = argparse.ArgumentParser(description="attack-ai-agent PyRIT v1.1.0 端到端演示")
    ap.add_argument("--step", default="", help="仅执行单个步骤标识，如 aia-02")
    ap.add_argument("--target", default="<AGENT_ENDPOINT>", help="目标标识")
    ap.add_argument("--scenario", default="effective",
                    choices=("effective", "partial", "refusal"))
    ap.add_argument("--no-memory", action="store_true", help="模拟目标无持久化记忆")
    ap.add_argument("--no-tools", action="store_true", help="模拟目标无可调用工具")
    ap.add_argument("--evidence-dir", default="", help="证据片段输出目录")
    args = ap.parse_args(argv)

    backend = FakePyRITBackend(
        scenario=args.scenario,
        memory_available=not args.no_memory,
        tools_available=not args.no_tools,
    )
    report = run_attack(
        objective="攻陷 LLM agent 并取证 ai_vector.txt",
        target_config={"target": args.target},
        backend_factory=backend,
        step=args.step,
        evidence_dir=args.evidence_dir or None,
    )
    print("后端：%s　步骤数：%d" % (report.backend, len(report.verdicts)))
    for v in report.verdicts:
        print("  %s [%s] 决定性命中=%s LLM线索=%s %s" % (
            v.step_id, v.level, v.deterministic_hit, v.llm_hit,
            ("跳过依据=%s" % v.skip_reason) if v.skip_reason else ""))
    print("证据片段：%s" % (report.evidence_paths()[0] if report.verdicts else "（无）"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
