#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""foothold-ad 命令行入口。

用法：
  python -m tools.foothold_ad.cli plan
  python -m tools.foothold_ad.cli preflight --artifacts artifacts/
  python -m tools.foothold_ad.cli verify --artifacts artifacts/
  python -m tools.foothold_ad.cli analyze --artifacts artifacts/ --steps ad-02,ad-05

退出码：0 = 通过；1 = 存在 BLOCKED / 校验失败 / 输入错误；2 = 用法错误。
"""
import argparse
import json
import sys
from typing import List, Optional

from . import evidence, preflight, provenance
from .model import BLOCKED, STEP_IDS, STEP_TITLES
from .runner import plan_steps, run


def _csv(value: Optional[str]) -> List[str]:
    if not value:
        return []
    return [item.strip() for item in value.split(",") if item.strip()]


def _emit(payload, out: Optional[str]) -> None:
    text = json.dumps(payload, ensure_ascii=False, indent=2)
    if out:
        with open(out, "w", encoding="utf-8") as handle:
            handle.write(text + "\n")
    else:
        print(text)


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(prog="foothold-ad", description="AD 域渗透判据与证据组装")
    sub = parser.add_subparsers(dest="command")

    sub.add_parser("plan", help="列出八个步骤")

    analyze = sub.add_parser("analyze", help="按工件目录输出步骤结论")
    analyze.add_argument("--artifacts", required=True, help="工件目录（directory/templates/trusts）")
    analyze.add_argument("--steps", help="逗号分隔的步骤子集，默认全部")
    analyze.add_argument("--owned", help="已控主体（逗号分隔），用于域管路径 BFS")
    analyze.add_argument("--out", help="结论 JSON 输出路径；缺省写 stdout")
    analyze.add_argument("--evidence-argv", action="store_true", help="附带每步 collect_evidence 参数")

    verify = sub.add_parser("verify", help="校验工件来源与完整性（artifact_manifest.json）")
    verify.add_argument("--artifacts", required=True, help="工件目录")
    verify.add_argument("--files", help="逗号分隔的待校验文件，缺省为核心三类 + 可选两类")
    verify.add_argument("--out", help="报告 JSON 输出路径；缺省写 stdout")

    pre = sub.add_parser("preflight", help="无真实环境时的采集前置清单")
    pre.add_argument("--artifacts", required=True, help="目标工件目录（可不存在）")
    pre.add_argument("--json", action="store_true", help="以 JSON 输出，缺省为人类可读清单")

    args = parser.parse_args(argv)
    if args.command == "plan":
        for step in STEP_IDS:
            print("%s\t%s" % (step, STEP_TITLES[step]))
        return 0
    if args.command == "preflight":
        payload = preflight.build(args.artifacts)
        if args.json:
            _emit(payload, None)
        else:
            print(preflight.render(payload))
        return 0
    if args.command == "verify":
        files = _csv(args.files) or None
        report = provenance.verify(args.artifacts, files=files)
        _emit(report.to_dict(), args.out)
        return 0 if report.ok else 1
    if args.command != "analyze":
        parser.print_usage()
        return 2

    try:
        steps = plan_steps(_csv(args.steps))
    except ValueError as exc:
        print("ERROR: %s" % exc, file=sys.stderr)
        return 2

    try:
        report = run(args.artifacts, steps=steps, owned=_csv(args.owned))
    except (OSError, ValueError) as exc:
        print("ERROR: %s" % exc, file=sys.stderr)
        return 1

    payload = report.to_dict()
    payload["digest"] = report.digest()
    if args.evidence_argv:
        payload["evidence_argv"] = {
            step: evidence.build_evidence_argv(result) for step, result in report.results.items()
        }
    _emit(payload, args.out)
    blocked = any(result.verdict == BLOCKED for result in report.results.values())
    return 1 if blocked else 0


if __name__ == "__main__":
    raise SystemExit(main())
