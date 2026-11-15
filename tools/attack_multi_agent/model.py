#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""值对象与常量（叶节点模块，不依赖包内其它模块）。

设计约束（`docs/operations/attack-multi-agent-design.md` §2）：
  - 仅数据与纯计算，不做 IO；
  - 效果等级取值固定为四值，供 `grade` 与报告共用；
  - 敏感值识别用正则，不引入第三方库。
"""
import re
from dataclasses import dataclass, field
from typing import Any, Dict, Tuple

# 效果等级：四值互斥，语义见设计文档 AC-12
LEVELS: Tuple[str, ...] = ("完全生效", "部分生效", "未生效", "已跳过")

# 凭据/flag 形态：靶标侧凭据以 sk- 前缀 + 长随机串出现（沿用上游实测形态 T-3）
SECRET_PATTERN = re.compile(r"sk-[A-Za-z0-9]{16,}")
# ai_vector.txt flag 值形态（考试环境为任意非空串，留给执行时实测；此处仅作兜底命中）
FLAG_PATTERN = re.compile(r"(?:ai[_-]?vector|flag)[=:\s]+([A-Za-z0-9_\-]{6,})", re.IGNORECASE)

# 拓扑解析：agent / 消息总线 / 共享记忆后端的常见标识
_AGENT_RE = re.compile(r"(?:agent|智能体|节点)\s*[:：]?\s*([A-Za-z0-9_\-]{2,})", re.IGNORECASE)
_BUS_RE = re.compile(r"(kafka|rabbitmq|redis|duckdb|nats|pulsar|消息总线|bus)", re.IGNORECASE)
_MEMORY_KEY_RE = re.compile(r"(?:key|键|conv:)\s*[:：]?\s*([A-Za-z0-9_:.\-]{2,})", re.IGNORECASE)


def find_secrets(text):
    """返回文本中出现的敏感值（去重、保持出现顺序）。"""
    seen, out = set(), []
    for m in SECRET_PATTERN.finditer(text or ""):
        value = m.group(0)
        if value not in seen:
            seen.add(value)
            out.append(value)
    return out


def find_flags(text):
    """返回文本中出现的 ai_vector 类 flag 候选值。"""
    out = []
    for m in FLAG_PATTERN.finditer(text or ""):
        out.append(m.group(1))
    return out


def redact(text, keep=6):
    """脱敏：保留前缀与末位，其余替换为固定标记。"""
    if not text:
        return text
    if len(text) <= keep + 4:
        return text[:2] + "<REDACTED>"
    return text[:keep] + "<REDACTED>" + text[-2:]


def parse_topology(text):
    """从拓扑发现输出中抽取 agent/bus/memory 要素，返回计数与样本。

    只抽取显式声明的字段，缺失即留空（不臆造）。
    """
    agents = set(_AGENT_RE.findall(text or ""))
    has_bus = bool(_BUS_RE.search(text or ""))
    memory_keys = _MEMORY_KEY_RE.findall(text or "")
    return {
        "agents": tuple(sorted(agents)),
        "agent_count": len(agents),
        "bus_present": has_bus,
        "memory_keys": tuple(memory_keys[:20]),
    }


def message_accepted(text):
    """消息操纵/冒充是否被接受：出现典型受理回执或转发/广播指示。"""
    return bool(re.search(r"(accepted|已接收|published|已发布|broadcast|转发|enqueued|acked)",
                          text or "", re.IGNORECASE))


def before_after_diff(before, after):
    """共享记忆/上下文投毒前后对照：返回是否发生可观测变更。"""
    if before is None or after is None:
        return False
    return bool(before) and bool(after) and before.strip() != after.strip()


@dataclass(frozen=True)
class Signals:
    """一步攻击的确定性信号集合（定级唯一输入）。

    字段判据见设计文档 AC-12：
      - `capability_missing`：目标不具备该能力（含被护栏拒绝且无替代路径）
      - `deterministic`：目标侧确定性信号是否命中（消息被受理/记忆被改写/差异非空）
      - `judge`：自有判据是否命中（下游动作偏离/flag 值命中/前后对照成立）
    """

    step_id: str
    deterministic: bool = False
    judge: bool = False
    capability_missing: bool = False
    consent_required: bool = False
    capped_partial: bool = False   # 仅本地自证、目标侧未生效 → 最高只能判「部分生效」
    detail: str = ""

    def as_dict(self):
        return {"step_id": self.step_id, "deterministic": self.deterministic,
                "judge": self.judge, "capability_missing": self.capability_missing,
                "consent_required": self.consent_required,
                "capped_partial": self.capped_partial, "detail": self.detail}


@dataclass(frozen=True)
class Observation:
    """一次工具交互的可观察结果（原始响应 + 解析后的信号）。"""

    raw: str = ""
    text: str = ""
    tool_result: str = ""
    telemetry: Dict[str, Any] = field(default_factory=dict)
    request: Dict[str, Any] = field(default_factory=dict)
    error: str = ""

    @property
    def secrets(self):
        return find_secrets(self.tool_result or self.text or self.raw)

    def as_dict(self):
        return {"text": self.text, "tool_result": self.tool_result,
                "telemetry": dict(self.telemetry), "error": self.error,
                "secrets": [redact(s) for s in self.secrets]}


@dataclass(frozen=True)
class StepVerdict:
    """一个步骤的对外结论（报告单元）。"""

    step_id: str
    path: str
    title: str
    level: str
    reason: str
    command: str
    observation: Observation
    evidence_path: str = ""

    def as_dict(self):
        return {"step_id": self.step_id, "path": self.path, "title": self.title,
                "level": self.level, "reason": self.reason,
                "command": self.command,
                "observation": self.observation.as_dict(),
                "evidence_path": self.evidence_path}


@dataclass(frozen=True)
class AttackRequest:
    """公开入口输入。"""

    target: str
    mode: str = "a2a-bus"          # a2a-bus | a2a-memory | a2a-orchestrator | agent-sse
    labs: Tuple[str, ...] = ("A2A_01",)
    paths: Tuple[str, ...] = ("A", "B", "C")
    step: str = ""
    evidence_dir: str = ""
    emit: bool = True
    use_pyrit: bool = False         # 仅对可达 A2A 端点做 PyRIT 深度补位时置真
    flag_value: str = ""            # 实测 ai_vector.txt 值（面板校验预言机等价双通道）


@dataclass(frozen=True)
class AttackReport:
    """公开入口输出。"""

    request: AttackRequest
    backend: str
    verdicts: Tuple[StepVerdict, ...] = ()
    object_graph: Dict[str, Any] = field(default_factory=dict)

    def levels(self):
        return tuple(v.level for v in self.verdicts)

    def evidence_paths(self):
        return tuple(v.evidence_path for v in self.verdicts)

    def as_dict(self):
        return {"target": self.request.target, "mode": self.request.mode,
                "backend": self.backend,
                "object_graph": dict(self.object_graph),
                "verdicts": [v.as_dict() for v in self.verdicts]}

    def by_step(self, step_id):
        for v in self.verdicts:
            if v.step_id == step_id:
                return v
        return None
