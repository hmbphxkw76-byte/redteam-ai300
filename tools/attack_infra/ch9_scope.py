#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Ch9 B3/B4：范围闸门与 OPSEC 建议集（AC-14..16）。

一手事实：`attack-infra-ch9-canonical.md` §3 P-3、C-4；Ch9 Warning L739/L1190。
纯判定/建议，不执行外部动作。
"""
from typing import Any, Dict, Tuple

from .ch9_model import BLOCKED, EXPOSED_NO_AUTH, Ch9Verdict

OPSEC_ADVICE: Tuple[str, ...] = (
    "会话名融入环境（避免 AWS-CLI-session-* 默认特征）",
    "以精确 filter-pattern / 目标化读取替代整流拉取与 --recursive",
    "角色验证优先用预期成功端点推断身份，减少 GetCallerIdentity 噪声",
)


def scope_gate(ctx: Any) -> Ch9Verdict:
    """sc-01（AC-14/15）：区分只读枚举与主动利用，越界主动动作阻断。"""
    resource = getattr(ctx, "discovered_resource", "")
    out_of_scope = bool(getattr(ctx, "out_of_scope", False))
    expansion = bool(getattr(ctx, "scope_expansion", False))
    active = bool(getattr(ctx, "active_action", False))  # 缺省关闭（AC-15）
    output = ("资源=%s\n跨项目=%s\n扩权授权=%s\n主动动作=%s"
              % (resource, out_of_scope, expansion, active))
    if out_of_scope and active and not expansion:
        return Ch9Verdict("ch9-scope", BLOCKED, "forbidden",
                          "跨项目主动利用缺扩权授权", "# 范围闸门判定", output,
                          {"action": "blocked", "resource": resource})
    if not active:
        return Ch9Verdict("ch9-scope", EXPOSED_NO_AUTH, "",
                          "只读枚举可用；主动探测未开启", "# 范围闸门判定", output,
                          {"action": "passive_discovery", "resource": resource})
    return Ch9Verdict("ch9-scope", EXPOSED_NO_AUTH, "",
                      "主动动作在授权范围内", "# 范围闸门判定", output,
                      {"action": "active", "resource": resource})


def opsec_advice(ctx: Any) -> Ch9Verdict:
    """sc-02（AC-16）：产出三项 OPSEC 建议。"""
    return Ch9Verdict("ch9-opsec", EXPOSED_NO_AUTH, "",
                      "%d 项 OPSEC 建议" % len(OPSEC_ADVICE),
                      "# 静态建议（不执行）", "\n".join("%d. %s" % (i + 1, a)
                                                   for i, a in enumerate(OPSEC_ADVICE)),
                      {"advice": list(OPSEC_ADVICE)})
