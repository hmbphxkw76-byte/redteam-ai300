#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""attack-multimodal CLI 演示（CI 零依赖）。

用法：
  python tools/attack_multimodal/demo.py --step multimodal-05 --target "<ENDPOINT>"
  python tools/attack_multimodal/demo.py --paths "A B C" --scenario effective
  python tools/attack_multimodal/demo.py --list
"""
import argparse
import json
import os
import sys

if __package__ in (None, ""):
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(
        os.path.abspath(__file__)))))
    from tools.attack_multimodal.backends import get_backend
    from tools.attack_multimodal.runner import grade, run_steps, summary
    from tools.attack_multimodal.steps import STEP_IDS, STEP_SPECS
else:
    from .backends import get_backend
    from .runner import grade, run_steps, summary
    from .steps import STEP_IDS, STEP_SPECS


def build_parser():
    ap = argparse.ArgumentParser(description="attack-multimodal 演示（PyRIT 1.1.0 seam）")
    ap.add_argument("--step", help="单步标识，如 multimodal-05")
    ap.add_argument("--target", default="<TARGET_ENDPOINT>",
                    help="目标端点标识（copy/paste 复现用；本演示不真实连接）")
    ap.add_argument("--paths", help="路径集合，如 'A B C'")
    ap.add_argument("--scenario", default="effective",
                    choices=["effective", "partial", "undetermined", "llm"])
    ap.add_argument("--real", action="store_true", help="真实后端（需 pyrit==1.1.0）")
    ap.add_argument("--list", action="store_true", help="列出步骤契约")
    return ap


def main(argv=None):
    args = build_parser().parse_args(argv)
    if args.list:
        print(json.dumps([s.step_id for s in STEP_SPECS], ensure_ascii=False))
        return 0
    if args.step and args.step not in STEP_IDS:
        print("未知步骤标识: %s" % args.step)
        return 2
    # scenario 仅对假后端有意义；真实后端不接受该关键字（避免 --real 启动时 TypeError）。
    backend = (get_backend(real=True) if args.real
               else get_backend(real=False, scenario=args.scenario))
    results = run_steps(step_ids=[args.step] if args.step else None,
                        paths=args.paths.split() if args.paths else None,
                        backend=backend)
    report = {
        "backend": backend.describe(),
        "results": [{"step_id": r.step_id, "grade": grade(r.response),
                     "verdict": r.response.verdict, "command": r.evidence["command"]}
                    for r in results],
        "summary": summary(results),
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
