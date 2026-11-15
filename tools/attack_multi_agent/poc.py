#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""示意脚本共享薄壳（SKILL.md「示意脚本，须记录来源」的公共部分）。

单一事实源（C1）：命令渲染与 HTTP 执行全部委托 `a2a.py` 与 `transport.py`；
本模块只统一**退出码**、**输出格式**与**错误收敛**，供下列 5 个顶层薄壳复用：

  - `tools/msg_inject.py`       （a2a-02 消息操纵）
  - `tools/agent_impersonate.py`（a2a-03 智能体冒充）
  - `tools/memory_poison.py`    （a2a-04 共享记忆投毒）
  - `tools/context_poison.py`   （a2a-05 上下文投毒）
  - `tools/workflow_disrupt.py` （a2a-06 工作流破坏）

薄壳不写证据：证据由 `tools/attack_multi_agent.runner` 统一经
`tools/collect_evidence.py` 契约落盘（C1 不重复实现格式）。
"""
import json

EXIT_OK = 0
EXIT_USAGE = 2
EXIT_UNREACHABLE = 3


def build_client(dry_run=False):
    """生产客户端；`--dry-run` 时返回只渲染命令的替身（离线可用）。"""
    from .transport import DryRunClient, UrllibHttpClient
    return DryRunClient() if dry_run else UrllibHttpClient()


def run(obs, command, json_mode=False, dry_run=False):
    """输出「命令 + 响应」，返回退出码（0 成功 / 3 目标不可达）。"""
    payload = {
        "step_command": command,
        "response": obs.text,
        "error": obs.error,
        "request": obs.request,
        "dry_run": bool(dry_run),
    }
    if json_mode:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print("[命令] %s" % command)
        if dry_run:
            print("[响应] （dry-run：未发送请求）")
        else:
            print("[响应] %s" % (obs.text or obs.error or "（空）"))
    if obs.error and not dry_run:
        return EXIT_UNREACHABLE
    return EXIT_OK
