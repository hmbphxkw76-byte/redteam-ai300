#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""threat-model 领域模型（纯数据，无外部依赖）。

本模块是威胁建模领域类型与计分契约的**唯一定义处**；不 import 本项目任何模块，
其余模块只 import 本模块 → 依赖图无环。

计分表依据 GOVERNANCE §2.2/§2.3（AI向量机/独立机 15、传统向量机 10、域控 5 单次、
链式入口低杠杆、诱饵机 0）。术语见 GLOSSARY.md。
"""
from dataclasses import dataclass, field
from typing import Dict, List

# §2.2/§2.3 计分模型 → 分值
SCORE_TABLE = {
    "AI向量机": 15,
    "独立机": 15,
    "传统向量机": 10,
    "域控": 5,
    "链式入口": 5,
    "诱饵机": 0,
    "不可判定": 0,
}

# 排序优先级（越小越优先）：AI向量/独立并列最高，诱饵最后
RANK_INDEX = {
    "AI向量机": 0,
    "独立机": 0,
    "传统向量机": 1,
    "域控": 2,
    "链式入口": 3,
    "不可判定": 4,
    "诱饵机": 5,
}

SURFACE_DOMAINS = {"D%d" % i for i in range(1, 12)}
DECOY = "诱饵机"
UNKNOWN = "不可判定"

# 各计分分类的最短攻击阶段模板（入口→横向→提权→AI利用→flag）
STAGE_TEMPLATE = {
    "AI向量机": ["入口", "横向", "提权", "AI利用", "flag"],
    "独立机": ["入口", "横向", "提权", "AI利用", "flag"],
    "传统向量机": ["入口", "横向", "提权", "flag"],
    "域控": ["入口", "横向", "域控收敛", "flag(proof.txt)"],
    "链式入口": ["入口", "立足点"],
}

# 计分分类 → 依赖前置子技能（SKILL 执行体 §2 / 矩阵映射）
# AI向量机 覆盖 D3(agent)/D4(multi-agent)/D5(RAG)/D6(embeddings)/D7(MCP)/D9(infra)，
# 对应 SKILL 第 13 行「拉动 attack-rag / attack-embeddings / attack-infra 等链式子技能」。
SUBSKILL = {
    "AI向量机": ["attack-ai-agent", "attack-multi-agent", "attack-rag",
                 "attack-embeddings", "attack-mcp-tool", "attack-infra"],
    "独立机": ["attack-mcp-tool"],
    "传统向量机": ["foothold-traditional"],
    "域控": ["foothold-traditional"],
}

# 预估耗时（分钟，工程估值，用于路径排序参考，非官方）
EST_MINUTES = {
    "AI向量机": 90,
    "独立机": 90,
    "传统向量机": 60,
    "域控": 30,
    "链式入口": 30,
}


@dataclass
class AssetView:
    """富化后的资产视图：recon 七字段 + 分析师分类层。"""

    asset_id: str
    category: str = ""
    product: str = ""
    version: str = ""
    endpoint: str = ""
    credential_hint: str = ""
    evidence_step: str = ""
    score_class: str = UNKNOWN
    attack_surface: str = ""
    trust_zone: str = "未分类"
    reachable: bool = True
    foothold_required: bool = False
    depends_on: List[str] = field(default_factory=list)

    @property
    def score(self) -> int:
        return SCORE_TABLE.get(self.score_class, 0)

    @property
    def is_decoy(self) -> bool:
        return self.score_class == DECOY

    def rank_key(self):
        """排序键：分值降序 → 分类序 → 资产ID（稳定）。"""
        return (-self.score, RANK_INDEX.get(self.score_class, 99), self.asset_id)


@dataclass
class AttackPath:
    """一条最短攻击路径（起止 + 阶段 + 耗时 + 依赖子技能 + 可达性）。"""

    target_asset: str
    start_asset: str
    score_class: str
    stages: List[str]
    est_minutes: int
    depends_on: List[str]
    status: str  # 可达 / 待补


@dataclass
class DecoyVerdict:
    """单台资产的诱饵判定（三维度 + ≤30min 时间盒 + 时间戳）。"""

    asset_id: str
    verdict: str  # 诱饵机 / 非诱饵 / 判定不确定
    dims: Dict[str, bool]
    elapsed_minutes: float
    timebox_minutes: int
    abandoned: bool
    reason: str
    timestamp: str


@dataclass
class ThreatModel:
    """威胁模型聚合体（四节 + 质量门）。"""

    target: str
    high_value: List[AssetView]  # 计分排序结果（含诱饵 0 分置底，供 §1 排序节展示）
    boundaries: Dict[str, List[str]]
    paths: List[AttackPath]
    decoys: List[DecoyVerdict]
    graph: Dict
    order: List[str]
    notes: List[str] = field(default_factory=list)

    def quality_gate(self):
        """返回缺失的质量门项列表；空列表即四项齐全（SKILL 第四节）。

        注：decoys 判空用 `is None`（区别于其余项的 falsy 判空）——空诱饵清单是
        合法状态（目标无诱饵嫌疑，render 输出「未提供诱饵嫌疑资产」占位），
        仅当构建未执行（decoys 为 None）时才算「诱饵判定清单」缺失。
        """
        missing = []
        if not self.high_value:
            missing.append("高价值资产清单")
        if not self.boundaries or not self.paths:
            missing.append("信任边界+最短攻击路径")
        if self.decoys is None:
            missing.append("诱饵判定清单")
        if not self.graph or not self.order:
            missing.append("优先级攻击图")
        return missing
