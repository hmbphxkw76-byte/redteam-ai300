"""命令行薄封装（S-1 入口的 CLI 形态）。"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .manifest import ManifestError, UsageError, load_manifest
from .runner import run_plan
from .summary import render_markdown


def main(argv=None, runner=None) -> int:
    """S-1 统一编排入口：CLI 与库调用共用；runner 可注入以替换真实脚本调用。"""
    ap = argparse.ArgumentParser(prog="tooling-automate", description="红队演练编排层")
    ap.add_argument("--manifest", required=True, help="任务清单 JSON 路径")
    ap.add_argument("--out", default="-", help="汇总 markdown 路径；- 表示 stdout")
    ap.add_argument("--dry-run", action="store_true", help="仅打印步骤序列不执行")
    ap.add_argument("--no-strict", dest="strict", action="store_false",
                    help="关闭 collect_evidence --strict")
    args = ap.parse_args(argv)
    try:
        manifest = load_manifest(Path(args.manifest))
    except UsageError as exc:
        print("用法错误: %s" % exc, file=sys.stderr)
        return 2
    except ManifestError as exc:
        print("清单错误: %s" % exc, file=sys.stderr)
        return 2
    result = run_plan(manifest, runner=runner, strict=args.strict, dry_run=args.dry_run)
    text = render_markdown(result, args.out, manifest)
    if args.out == "-":
        sys.stdout.write(text)
    return result.exit_code
