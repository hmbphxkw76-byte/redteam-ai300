#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""G1 MCP 源码后门规划（课件 Ch8 §8.1 Listing 1-9 / 自研确定性实现）。

产出五要素记录：研读合法 server → 选高频 helper → 伪装身份提交 → 推送 → 等待窗口。
不生成真实恶意载荷、不接触任何目标仓库；`runner` 注入点供测试捕获命令，默认不执行。
"""
from dataclasses import dataclass, field


@dataclass
class BackdoorPlan:
    server: str
    helper: str
    author_name: str
    author_email: str
    commit_msg: str
    wait_max_minutes: int = 4
    elements: dict = field(default_factory=dict)
    source: str = "Ch8 §8.1 Listing 1-9"


def build_plan(server, helper, author_name, author_email, commit_msg="minor change",
               wait_max_minutes=4):
    """给定合法 server 结构与身份，产出五要素后门规划记录。"""
    if not server or not helper:
        raise ValueError("server 与 helper 不得为空")
    plan = BackdoorPlan(server, helper, author_name, author_email,
                        commit_msg, wait_max_minutes)
    plan.elements = {
        "研读合法server": "FastMCP / @mcp.tool() / docstring 即工具描述",
        "选高频helper": helper,
        "伪装身份提交": "%s <%s> / %s" % (author_name, author_email, commit_msg),
        "推送触发": "git push origin main → 自动脚本更新 → agent 调用触发",
        "等待窗口": "nc 监听；自动脚本最长约 %d 分钟触发" % wait_max_minutes,
    }
    return plan


def commands(plan, runner=None):
    """返回可 copy/paste 的命令序列；runner 仅记录不执行（默认）。"""
    cmds = [
        "git clone <LEGIT_SERVER_URL>",
        "# 编辑 %s：在 %s 中植入后门" % (plan.server, plan.helper),
        "git config user.name '%s'" % plan.author_name,
        "git config user.email '%s'" % plan.author_email,
        'git commit -m "%s"' % plan.commit_msg,
        "git push origin main",
        "nc -nvlkp <LPORT>",
    ]
    if runner is not None:
        for c in cmds:
            runner(c)
    return cmds


def main():
    import argparse, json
    p = argparse.ArgumentParser(description="G1 MCP 源码后门规划")
    p.add_argument("--server", required=True)
    p.add_argument("--helper", required=True)
    p.add_argument("--author", required=True)
    p.add_argument("--email", required=True)
    a = p.parse_args()
    print(json.dumps(build_plan(a.server, a.helper, a.author, a.email).__dict__,
                     ensure_ascii=False, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
