#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Ch5 增量步骤命令行薄壳（rag-06..rag-09）。

证据「确切命令」指向本文件，保证技术读者可 copy/paste 复现（B5）。
"""
import argparse
import json
import os
import sys

if __package__ in (None, ""):
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(
        os.path.abspath(__file__)))))

from tools.attack_rag import AttackRequest, run_ch5  # noqa: E402
from tools.attack_rag.ch5 import CH5_STEP_IDS  # noqa: E402


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Ch5 Exploiting RAG Pipelines 增量步骤执行器（attack-rag）")
    parser.add_argument("--step", choices=list(CH5_STEP_IDS), default="",
                        help="仅执行单步；缺省执行全部四步")
    parser.add_argument("--target", default="rag-ch5")
    parser.add_argument("--evidence-dir", default="")
    parser.add_argument("--no-emit", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    request = AttackRequest(target=args.target, step=args.step,
                            evidence_dir=args.evidence_dir, emit=not args.no_emit)
    report = run_ch5(request)
    if args.json:
        print(json.dumps(report.as_dict(), ensure_ascii=False, indent=2))
    else:
        for verdict in report.verdicts:
            print("%s [%s] %s" % (verdict.step_id, verdict.level, verdict.reason))
    return 0


if __name__ == "__main__":
    sys.exit(main())
