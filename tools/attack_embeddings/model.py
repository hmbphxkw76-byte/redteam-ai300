#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""attack-embeddings 值对象与常量（叶节点，无 IO、无第三方依赖）。

设计约束（`docs/operations/attack-embeddings-design.md` §1/§6）：
  - 仅数据与纯计算；不触碰网络或文件系统；
  - 效果等级沿用仓库四值约定（与 `attack-mcp-tool` 对齐）；
  - 向量运算用标准库实现，便于零依赖测试。
"""
import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

# 效果等级：四值互斥，语义见规格 v2 AC-1..AC-11。
LEVELS: Tuple[str, ...] = ("完全生效", "部分生效", "未生效", "已跳过")

# embedding 步骤（与 skills/attack-embeddings/SKILL.md 的 emb-01..emb-08 对齐）。
STEP_IDS: Tuple[str, ...] = tuple("emb-0%d" % i for i in range(1, 9))


def cosine(a: List[float], b: List[float]) -> float:
    """余弦相似度；任一零向量返回 0.0（不抛异常）。"""
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0.0 or nb == 0.0:
        return 0.0
    return dot / (na * nb)


def l2(a: List[float], b: List[float]) -> float:
    """欧氏距离。"""
    return math.sqrt(sum((x - y) ** 2 for x, y in zip(a, b)))


@dataclass
class AttackRequest:
    """一次 attack-embeddings 演练的输入。"""
    target: str = "http://local-fixture"
    embed_api: str = ""              # 显式 embedding 端点；空则使用本地夹具
    vector_store: str = "memory"     # memory / faiss / chroma / pgvector
    sample: str = ""                 # 成员推断的目标样本
    concept: str = ""                # 向量库反查的目标概念
    flag: str = ""                   # 已知 ai_vector.txt 值（双通道核验用）
    has_surface: bool = True         # False 时走降级路径（AC-11）
    mode: str = "full"               # full / degraded


@dataclass
class StepVerdict:
    """单个步骤的判定结果。"""
    step_id: str
    level: str
    summary: str
    metrics: Dict[str, float] = field(default_factory=dict)
    evidence_path: str = ""

    def __post_init__(self):
        if self.level not in LEVELS:
            raise ValueError("非法效果等级：%r（应为 %s）" % (self.level, LEVELS))


@dataclass
class Finding:
    """跨步骤的可披露结论。"""
    concept: str
    score: float
    detail: str = ""


@dataclass
class AttackReport:
    """一次演练的结构化报告。"""
    degraded: bool = False
    steps: List[StepVerdict] = field(default_factory=list)
    findings: List[Finding] = field(default_factory=list)
    notes: List[str] = field(default_factory=list)

    def levels(self) -> Dict[str, str]:
        return {s.step_id: s.level for s in self.steps}

    def confirmed(self) -> bool:
        return any(s.level == "完全生效" for s in self.steps)


def safe_samples(text: str) -> List[str]:
    """把散文拆成 token 列表；空串返回空列表。"""
    return [t for t in (text or "").split() if t]
