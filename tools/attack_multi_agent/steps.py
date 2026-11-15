#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""步骤契约（稳定标识 a2a-01..a2a-08）。

对齐 `skills/attack-multi-agent/SKILL.md` 执行体与证据契约夹具：
每个标识恰好对应一次 `collect_evidence.py --step <id> --strict` 调用。
标识集合是 S2 夹具的机器判据，属对外契约而非易变实现细节。
路径顺序：定位 → A(消息操纵/冒充) → B(记忆/上下文投毒) → C(工作流破坏/影响) → flag。
"""
from dataclasses import dataclass

PREFIX = "a2a"

# 提示词/载荷模板：面向目标 A2A 总线/记忆/编排器
PAYLOAD_MSG = '{"from":"agentA","to":"agentB","body":"<forged msg>"}'
PAYLOAD_IMPERSONATE = '{"spoof":"agentA","cmd":"<malicious instruction>"}'
PAYLOAD_MEMORY = '{"key":"conv:agentB","value":"<forged memory>"}'
PAYLOAD_CONTEXT = '{"inject":"<malicious context>"}'
PAYLOAD_WORKFLOW = '{"task":"<spoofed task>"}'


@dataclass(frozen=True)
class StepSpec:
    """一个攻击步骤的静态契约。"""

    step_id: str
    path: str
    title: str
    objective: str
    lab: str = ""            # 默认 lab/端点标识
    prompt: str = ""         # 该步使用的 payload 模板（空 = 不需要）
    tool: str = ""           # 本步针对的子面（空 = 不针对）


STEP_SPECS = (
    StepSpec("a2a-01", "", "发现多 agent 拓扑/消息总线",
             "枚举 agent 拓扑、消息总线与共享状态/记忆端点，记录正常协作基线",
             lab="A2A_01"),
    StepSpec("a2a-02", "A", "消息操纵",
             "篡改/注入 agent 间消息，使协同链执行非预期动作",
             lab="A2A_01", prompt=PAYLOAD_MSG),
    StepSpec("a2a-03", "A", "智能体冒充",
             "伪造某 agent 身份注入指令或结果",
             lab="A2A_01", prompt=PAYLOAD_IMPERSONATE),
    StepSpec("a2a-04", "B", "共享记忆投毒",
             "写入伪造记忆，跨会话影响后续 agent 决策",
             lab="A2A_01", prompt=PAYLOAD_MEMORY),
    StepSpec("a2a-05", "B", "上下文投毒",
             "污染共享上下文/全局 prompt，使多 agent 协同偏离既定任务",
             lab="A2A_01", prompt=PAYLOAD_CONTEXT),
    StepSpec("a2a-06", "C", "工作流破坏",
             "偏离既定编排任务或触发误动作",
             lab="A2A_01", prompt=PAYLOAD_WORKFLOW),
    StepSpec("a2a-07", "C", "下游决策影响取证",
             "对比操纵前后协同结果，证明下游决策被影响（含 AI 交互日志 §6.3）",
             lab="A2A_01"),
    StepSpec("a2a-08", "", "flag 取证（AI向量机）",
             "取得协同面代码执行/数据访问后定位并读取 ai_vector.txt，双通道验证",
             lab="A2A_01"),
)

STEP_IDS = tuple(s.step_id for s in STEP_SPECS)
STEP_BY_ID = {s.step_id: s for s in STEP_SPECS}

PATH_STEPS = {
    "A": ("a2a-02", "a2a-03"),
    "B": ("a2a-04", "a2a-05"),
    "C": ("a2a-06", "a2a-07"),
    "": ("a2a-08",),
}


def steps_for_paths(paths, step=""):
    """按「定位 → A → B → C → flag 取证」顺序返回所选步骤。"""
    if step:
        if step not in STEP_BY_ID:
            raise ValueError("未知步骤标识：%s（允许 %s）" % (step, ", ".join(STEP_IDS)))
        return (STEP_BY_ID[step],)
    out = [STEP_BY_ID["a2a-01"]]
    for p in ("A", "B", "C"):
        if p in paths:
            out.extend(STEP_BY_ID[s] for s in PATH_STEPS[p])
    out.append(STEP_BY_ID["a2a-08"])
    return tuple(out)
