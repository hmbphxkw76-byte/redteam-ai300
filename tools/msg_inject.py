#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""a2a-02 消息操纵示意脚本（SKILL.md 攻击路径 A 第 2 步）。

首方薄壳：参数解析与输出在 `tools/attack_multi_agent/poc.py`，命令渲染与执行
全部委托 `tools/attack_multi_agent/a2a.py`（单一事实源 C1，不重复实现）。
来源：本仓库首方实现（证据 `--script tools/msg_inject.py` 可记载此路径）。

用法（对齐 SKILL.md）：
  python tools/msg_inject.py --bus <BUS> --from agentA --to agentB --payload "<forged msg>"
  python tools/msg_inject.py --bus <BUS> --from agentA --to agentB --payload "..." --dry-run

退出码：0 成功；2 入参错误；3 目标不可达。
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools.attack_multi_agent import poc  # noqa: E402
from tools.attack_multi_agent.a2a import A2ABusClient  # noqa: E402


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="a2a-02 A2A 消息操纵")
    ap.add_argument("--bus", required=True, help="消息总线基址")
    ap.add_argument("--from", dest="src", required=True, help="冒充的来源 agent")
    ap.add_argument("--to", dest="dst", required=True, help="目标 agent")
    ap.add_argument("--payload", required=True, help="伪造消息体")
    ap.add_argument("--dry-run", action="store_true", help="只渲染命令，不发请求")
    ap.add_argument("--json", action="store_true", help="JSON 输出")
    args = ap.parse_args(argv)

    client = poc.build_client(args.dry_run)
    obs, cmd = A2ABusClient(client, args.bus).inject_message(args.src, args.dst, args.payload)
    return poc.run(obs, cmd, json_mode=args.json, dry_run=args.dry_run)


if __name__ == "__main__":
    sys.exit(main())
