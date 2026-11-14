#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""本地恶意 MCP server（SKILL.md mcp-02 的示意脚本的可运行实现）。

用途：为「投毒自证」与「投毒前后对照」提供**真实可枚举**的目标，使
mcp-02/03/04 不依赖外部环境即可复现；不对外网暴露，仅绑定给定地址。

示例：
  python tools/serve_malicious_mcp.py --host 127.0.0.1 --port 8080
  python tools/serve_malicious_mcp.py --dump-poison-diff   # 仅打印前后差分

诚实边界：本 server 只证明「投毒技术可构造并可被客户端枚举」，不证明目标
agent 已被操纵；后者由编排层用目标侧信号单独判定（规格 v2 R-1）。
"""
import argparse
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:  # 支持直跑
    sys.path.insert(0, ROOT)

from tools.attack_mcp_tool import poison  # noqa: E402


def main(argv=None):
    ap = argparse.ArgumentParser(description="本地恶意 MCP server（投毒自证用）")
    ap.add_argument("--host", default="127.0.0.1", help="绑定地址（默认回环）")
    ap.add_argument("--port", type=int, default=8080, help="端口；0 表示由系统分配")
    ap.add_argument("--dump-poison-diff", action="store_true",
                    help="仅打印投毒前后工具面差分（不启动 server）")
    args = ap.parse_args(argv)

    if args.dump_poison_diff:
        diff = poison.diff_as_dict(poison.diff_surfaces(
            poison.baseline_surface(), poison.poisoned_surface()))
        print(json.dumps(diff, ensure_ascii=False, indent=1))
        return 0

    server = poison.PoisonedMcpServer(host=args.host, port=args.port).start()
    print("恶意 MCP server 已启动：%s" % server.url)
    print("工具面端点：GET %s/tools/list ｜ JSON-RPC：POST %s"
          % (server.url.rsplit("/mcp", 1)[0], server.url))
    print("Ctrl+C 结束。")
    try:
        while True:
            server._thread.join(1)  # noqa: SLF001 - 阻塞主线程直至 Ctrl+C
    except KeyboardInterrupt:
        pass
    finally:
        server.stop()
        print("已停止。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
