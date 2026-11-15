#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""attack-embeddings 命令行入口（零外部依赖）。

用法：
  python -m tools.attack_embeddings.cli --sample "salary executive package secret"
  python -m tools.attack_embeddings.cli --degraded      # AC-11 降级路径
"""
import argparse
import sys

from .model import AttackRequest
from .runner import run_attack


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="attack-embeddings 演练入口")
    ap.add_argument("--target", default="http://local-fixture")
    ap.add_argument("--sample", default="")
    ap.add_argument("--concept", default="")
    ap.add_argument("--flag", default="")
    ap.add_argument("--degraded", action="store_true",
                    help="模拟无 embedding 面（AC-11 降级）")
    args = ap.parse_args(argv)

    req = AttackRequest(target=args.target, sample=args.sample,
                        concept=args.concept, flag=args.flag,
                        has_surface=not args.degraded)
    report = run_attack(req)

    print("degraded=%s confirmed=%s" % (report.degraded, report.confirmed()))
    for s in report.steps:
        print("  %s [%s] %s" % (s.step_id, s.level, s.summary))
    for f in report.findings:
        print("  finding %s: %.3f %s" % (f.concept, f.score, f.detail))
    return 0


if __name__ == "__main__":
    sys.exit(main())
