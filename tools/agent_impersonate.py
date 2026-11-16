#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""a2a-03 智能体冒充示意脚本（SKILL.md 攻击路径 A 第 3 步）。

首方薄壳：参数解析与输出在 `tools/attack_multi_agent/poc.py`，命令渲染与执行
全部委托 `tools/attack_multi_agent/a2a.py`（单一事实源 C1）。
来源：本仓库首方实现（证据 `--script tools/agent_impersonate.py` 可记载此路径）。

用法（对齐 SKILL.md）：
  python tools/agent_impersonate.py --bus <BUS> --spoof agentA --cmd "<malicious instruction>"
  python tools/agent_impersonate.py --bus <BUS> --spoof agentA --cmd "..." --dry-run

退出码：0 成功；2 入参错误；3 目标不可达。
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools.attack_multi_agent import poc  # noqa: E402
from tools.attack_multi_agent.a2a import A2ABusClient  # noqa: E402


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="a2a-03 A2A 智能体冒充")
    ap.add_argument("--bus", required=True, help="消息总线基址")
    ap.add_argument("--spoof", required=True, help="被冒充的 agent 身份")
    ap.add_argument("--cmd", required=True, help="以该身份注入的指令")
    ap.add_argument("--dry-run", action="store_true", help="只渲染命令，不发请求")
    ap.add_argument("--json", action="store_true", help="JSON 输出")
    args = ap.parse_args(argv)

    client = poc.build_client(args.dry_run)
    obs, cmd = A2ABusClient(client, args.bus).impersonate(args.spoof, args.cmd)
    return poc.run(obs, cmd, json_mode=args.json, dry_run=args.dry_run)


if __name__ == "__main__":
    sys.exit(main())
