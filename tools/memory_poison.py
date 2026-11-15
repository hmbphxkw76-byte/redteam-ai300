#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""a2a-04 共享记忆投毒示意脚本（SKILL.md 攻击路径 B 第 4 步）。

首方薄壳：参数解析与输出在 `tools/attack_multi_agent/poc.py`，命令渲染与执行
全部委托 `tools/attack_multi_agent/a2a.py`（单一事实源 C1）。
来源：本仓库首方实现（证据 `--script tools/memory_poison.py` 可记载此路径）。

用法（对齐 SKILL.md）：
  python tools/memory_poison.py --store <MEMORY> --key conv:agentB --value "<forged memory>"
  python tools/memory_poison.py --store <MEMORY> --key conv:agentB --value "..." --before

`--before` 先读一次原值再写入，直接形成「操纵前后对照」（SKILL 质量门要求）。

退出码：0 成功；2 入参错误；3 目标不可达。
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools.attack_multi_agent import poc  # noqa: E402
from tools.attack_multi_agent.a2a import MemoryStoreClient  # noqa: E402


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="a2a-04 A2A 共享记忆投毒")
    ap.add_argument("--store", required=True, help="共享记忆/状态后端基址")
    ap.add_argument("--key", default="conv:agentB", help="记忆键")
    ap.add_argument("--value", required=True, help="写入的伪造记忆")
    ap.add_argument("--before", action="store_true", help="写入前读取原值（前后对照）")
    ap.add_argument("--dry-run", action="store_true", help="只渲染命令，不发请求")
    ap.add_argument("--json", action="store_true", help="JSON 输出")
    args = ap.parse_args(argv)

    client = poc.build_client(args.dry_run)
    store = MemoryStoreClient(client, args.store)
    before = ""
    if args.before and not args.dry_run:
        before, _ = store.read_memory(args.key)
    obs, cmd = store.poison_memory(args.key, args.value)
    if before:
        print("[投毒前] %s" % before)
    return poc.run(obs, cmd, json_mode=args.json, dry_run=args.dry_run)


if __name__ == "__main__":
    sys.exit(main())
