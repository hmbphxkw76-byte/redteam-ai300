#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""命令行入口（薄壳）：单步或全量执行，落盘证据并打印结论。

示例（演练目标，agent 会话形态）：
  python tools/attack_mcp_tool/cli.py --step mcp-01 --mode agent-sse \
      --target http://192.168.40.189 --lab MCP_01

示例（本地恶意 server 对照组，裸 JSON-RPC 形态）：
  python tools/serve_malicious_mcp.py --host 127.0.0.1 --port 8080 &
  python tools/attack_mcp_tool/cli.py --step mcp-02 --mode jsonrpc \
      --target http://127.0.0.1:8080/mcp

退出码：0 成功（含「已跳过」）；1 证据质量门失败；2 用法错误。
"""
import argparse
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if ROOT not in sys.path:  # 支持 `python tools/attack_mcp_tool/cli.py` 直跑
    sys.path.insert(0, ROOT)

from tools.attack_mcp_tool import Runtime, run_attack  # noqa: E402
from tools.attack_mcp_tool.model import AttackRequest  # noqa: E402
from tools.attack_mcp_tool.runner import DEFAULT_EVIDENCE_DIR  # noqa: E402
from tools.attack_mcp_tool.steps import STEP_IDS  # noqa: E402


def build_parser():
    ap = argparse.ArgumentParser(description="MCP 与工具面滥用执行器（attack-mcp-tool）")
    ap.add_argument("--target", required=True, help="演练目标入口或裸 MCP 端点")
    ap.add_argument("--mode", choices=("agent-sse", "jsonrpc"), default="agent-sse",
                    help="形态：agent-sse=会话 SSE；jsonrpc=裸 MCP JSON-RPC")
    ap.add_argument("--lab", action="append", default=None,
                    help="agent-sse 形态的 lab 标识（可重复）；缺省 MCP_01")
    ap.add_argument("--path", action="append", choices=("A", "B", "C"), default=None,
                    help="攻击路径（可重复）；缺省全选")
    ap.add_argument("--step", default="", help="仅执行单步：%s" % ", ".join(STEP_IDS))
    ap.add_argument("--evidence-dir", default=DEFAULT_EVIDENCE_DIR, help="证据片段输出目录")
    ap.add_argument("--no-emit", action="store_true", help="不落盘证据（仅取结论）")
    ap.add_argument("--no-shot", action="store_true", help="不截图（证据标待补录）")
    ap.add_argument("--browser", default=None, help="无头浏览器可执行文件路径")
    ap.add_argument("--json", action="store_true", help="输出机读 JSON 报告")
    return ap


def main(argv=None, runtime=None):
    """命令行主函数；`runtime` 可注入（测试用替身即离线，AC-18）。"""
    args = build_parser().parse_args(argv)
    request = AttackRequest(
        target=args.target, mode=args.mode,
        labs=tuple(args.lab or ("MCP_01",)),
        paths=tuple(args.path or ("A", "B", "C")),
        step=args.step, evidence_dir=args.evidence_dir, emit=not args.no_emit)
    if runtime is None:
        runtime = Runtime(browser_path=args.browser, shot_enabled=not args.no_shot)
    try:
        report = run_attack(request, runtime)
    except ValueError as exc:
        print("ERROR: %s" % exc, file=sys.stderr)
        return 2
    except RuntimeError as exc:
        print("ERROR: %s" % exc, file=sys.stderr)
        return 1

    if args.json:
        print(json.dumps(report.as_dict(), ensure_ascii=False, indent=1))
        return 0

    print("目标：%s　形态：%s　传输：%s" % (request.target, request.mode, report.backend))
    print("%-8s %-6s %-10s %s" % ("步骤", "路径", "效果等级", "依据"))
    for v in report.verdicts:
        print("%-8s %-6s %-10s %s" % (v.step_id, v.path or "—", v.level, v.reason))
        if v.evidence_path:
            print("         证据：%s" % v.evidence_path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
