#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Go/No-Go 门评估与决策矩阵（Ch10 §10.2 Table 9 / A5）。

每条路径的 Go/No-Go 取决于其依赖假设的状态；决策矩阵在时间压力下给出
信息可用/缺失、验证成本与 GO/HOLD 判定。纯函数，外部输入经参数注入。
"""
from .model import DecisionGate


def evaluate_gates(paths, assumptions):
    """按依赖假设状态为每条路径生成门（GO/HOLD/BLOCKED）。

    - 所有依赖假设 VALIDATED → GO
    - 任一 INVALIDATED → BLOCKED（假设被证伪，路径不再成立）
    - 存在 UNVALIDATED → HOLD（须先验证）
    """
    by_id = {a.id: a for a in (assumptions or [])}
    for path in paths or []:
        gates = []
        for g in path.gates:
            a = by_id.get(g.assumption_id)
            if a is None:
                decision = "HOLD"
                note = "依赖假设 %s 未登记" % g.assumption_id
            elif a.status == "VALIDATED":
                decision = "GO"
                note = "依赖假设已验证"
            elif a.status == "INVALIDATED":
                decision = "BLOCKED"
                note = "依赖假设被证伪"
            else:
                decision = "HOLD"
                note = "依赖假设未验证"
            gates.append(DecisionGate(assumption_id=g.assumption_id,
                                      decision=decision, note=note))
        path.gates = gates
        decisions = {g.decision for g in gates}
        if not gates:
            path.gate_decision = "BLOCKED" if path.gate_decision == "BLOCKED" else "GO"
        elif "BLOCKED" in decisions:
            path.gate_decision = "BLOCKED"
        elif "HOLD" in decisions:
            path.gate_decision = "HOLD"
        else:
            path.gate_decision = "GO"
    return paths


def go_no_go(paths, assumptions, remaining_days=None):
    """生成 Table 9 结构决策矩阵（四列：决策点/可用/缺失/成本/决定）。

    返回 dict：{rows: [[decision_point, available, missing, time_cost, decision]], ...}
    """
    by_id = {a.id: a for a in (assumptions or [])}
    rows = []
    for p in paths or []:
        missing, available = [], []
        for g in p.gates:
            a = by_id.get(g.assumption_id)
            if a is None:
                missing.append(g.assumption_id + "(未登记)")
            elif a.status == "VALIDATED":
                available.append(a.id)
            else:
                missing.append(a.id + "(%s)" % a.status)
        cost = "依赖验证" if missing else "0"
        if remaining_days is not None and missing and remaining_days <= 2:
            decision = "HOLD"  # 时间不足时不启动需验证路径
        else:
            decision = p.gate_decision if p.gate_decision in ("GO", "HOLD", "BLOCKED") else "GO"
        rows.append([
            "执行 %s → %s" % (p.start_asset, p.target_asset),
            "、".join(available) or "无",
            "、".join(missing) or "无",
            cost,
            decision,
        ])
    return {"remaining_days": remaining_days, "rows": rows}
