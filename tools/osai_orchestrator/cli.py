"""CLI 薄封装：S-1 入口的命令行形态，runner 可注入以测试。"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .runner import Orchestrator


def _load_config(path: str | None) -> dict:
    if not path:
        return {}
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("config must be a JSON object")
    return data


def main(argv=None, runner=None) -> int:
    ap = argparse.ArgumentParser(prog="osai-orchestrator", description="OSAI 考试编排与韧性增强层")
    ap.add_argument("--config", help="可选 JSON 配置路径")
    ap.add_argument("--plan", action="store_true", help="打印能力域清单（dry run，无副作用）")
    ap.add_argument("--anonymize", help="对给定文本执行匿名化并返回结果")
    args = ap.parse_args(argv)

    try:
        config = _load_config(args.config)
    except (OSError, ValueError) as exc:
        print("config error: %s" % exc, file=sys.stderr)
        return 2

    orch = Orchestrator()
    if args.plan:
        capabilities = [
            "execution-monitor", "reflector", "tool-budget", "barrier", "planner",
            "refiner", "human-in-loop", "summary-marker", "context-compaction",
            "anonymizer", "memory-whitelist", "independent-review", "template-overlay",
            "ontology", "typed-registry", "call-id-normalizer", "error-classifier",
            "retry-policy", "bounded-retriever",
        ]
        print("\n".join(capabilities))
        return 0
    if args.anonymize is not None:
        print(orch.anonymize(args.anonymize))
        return 0
    print("no action specified; use --plan or --anonymize", file=sys.stderr)
    return 2
