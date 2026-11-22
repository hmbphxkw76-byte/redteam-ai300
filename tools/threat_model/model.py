#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""threat-model 领域模型（纯数据，无外部依赖）。

本模块是威胁建模领域类型与计分契约的**唯一定义处**；不 import 本项目任何模块，
其余模块只 import 本模块 → 依赖图无环。

计分表依据 GOVERNANCE §2.2/§2.3（AI向量机/独立机 15、传统向量机 10、域控 5 单次、
链式入口低杠杆、诱饵机 0）。术语见 GLOSSARY.md。

Ch10 对齐增量：Assumption / TrustBoundary / DecisionGate / ATLASMap 四类 + 既有
AssetView / AttackPath / ThreatModel 字段扩展；所有新增为增量，既有语义不变。
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

# ---- Ch10 对齐新增常量 ----
ASSUMPTION_STATUSES = ("UNVALIDATED", "VALIDATED", "INVALIDATED")
VALIDATION_STATUSES = ("VALIDATED", "UNVALIDATED", "INFERRED")
CONFIDENCE_LEVELS = ("HIGH", "MEDIUM", "LOW")
PATH_STATUSES = ("GO", "HOLD", "BLOCKED")
ACCESS_STATUSES = ("OBTAINED", "ACCESSIBLE", "UNVALIDATED", "BEHIND_N_BOUNDARIES")
# Ch10 Table 6 七个 ATLAS 技术 ID（唯一集合，映射模块不得引入集外 ID）
ATLAS_IDS = ("AML.T0044", "AML.T0025", "AML.T0020", "AML.T0048",
             "AML.T0043", "AML.T0010", "AML.T0040")
# 6 段简报标题（Listing 8）
BRIEF_SECTIONS = ("TARGET SUMMARY", "CROWN JEWELS", "ASSUMPTION REGISTER STATUS",
                  "SCOPE CONSTRAINTS", "ESCALATION PATHS", "NEXT ACTIONS")


@dataclass
class Assumption:
    """假设登记册条目（Ch10 Table 1 六字段 + 桶标记）。"""

    id: str
    observation: str
    hypothesis: str
    confidence: str = "MEDIUM"
    source: str = ""
    status: str = "UNVALIDATED"
    bucket: str = "attack_plan"  # attack_plan / verification_task

    def as_row(self):
        return [self.id, self.observation, self.hypothesis,
                self.confidence, self.source, self.status]


@dataclass
class TrustBoundary:
    """信任边界五要素（Ch10 Table 8）+ 身份塌缩 / 信任缺口标记。"""

    id: str
    from_component: str
    to_component: str
    trust_type: str = ""
    enforcement: str = ""
    validation_status: str = "UNVALIDATED"
    offensive_implication: str = ""
    identity_collapse: bool = False
    is_gap: bool = False  # enforcement 缺失 → TRUST_GAP

    def as_row(self):
        return [self.id, "%s → %s" % (self.from_component, self.to_component),
                self.trust_type, self.enforcement or "无",
                self.validation_status, self.offensive_implication]


@dataclass
class DecisionGate:
    """Go/No-Go 门（Ch10 Path 1/2/3）：依赖假设 + 判定。"""

    assumption_id: str
    decision: str = "HOLD"  # GO / HOLD / BLOCKED
    note: str = ""


@dataclass
class ATLASMap:
    """组件→ATLAS 技术映射（Ch10 Table 6）+ 适用性前置门槛。"""

    component: str
    technique: str
    technique_id: str
    application: str = ""
    precondition_id: str = ""
    immediately_applicable: bool = False

    def applicability(self):
        return "立即适用" if self.immediately_applicable else "applicable if"

    def as_row(self):
        return [self.component, self.technique, self.technique_id,
                self.applicability(), self.application]


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
    # Ch10 增量（不改动既有七字段语义）
    observations: List[Dict] = field(default_factory=list)
    offensive_value: str = ""
    access_status: str = ""
    path_gates: List[str] = field(default_factory=list)
    detection_risk: str = ""

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
    status: str  # 可达 / 待补（既有）；GO / HOLD / BLOCKED（Ch10 增量）
    # Ch10 增量
    boundary_crossings: List[str] = field(default_factory=list)
    gates: List[DecisionGate] = field(default_factory=list)
    detection_risk: str = ""
    gate_decision: str = ""  # Ch10 Go/No-Go：GO / HOLD / BLOCKED（不改既有 status）

    def is_prohibited(self):
        """RoE 硬过滤判据：gate_decision=BLOCKED 即被禁止。"""
        return self.gate_decision == "BLOCKED"


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
    """威胁模型聚合体（四节 + 质量门 + Ch10 增量节）。"""

    target: str
    high_value: List[AssetView]
    boundaries: Dict[str, List[str]]
    paths: List[AttackPath]
    decoys: List[DecoyVerdict]
    graph: Dict
    order: List[str]
    notes: List[str] = field(default_factory=list)
    # Ch10 增量（均为可选，默认空/0 保证既有调用方零破坏）
    assumptions: List[Assumption] = field(default_factory=list)
    trust_boundaries: List[TrustBoundary] = field(default_factory=list)
    atlas_map: List[ATLASMap] = field(default_factory=list)
    decision_matrix: Dict = field(default_factory=dict)
    report_findings: List[str] = field(default_factory=list)
    revision: int = 1
    decision_log: List[str] = field(default_factory=list)
    brief_version: str = "1.0"
    engagement_day: int = 1

    def quality_gate(self):
        """返回缺失的质量门项列表；空列表即四项齐全（SKILL 第四节）。

        注：decoys 判空用 `is None`（区别于其余项的 falsy 判空）——空诱饵清单是
        合法状态（目标无诱饵嫌疑，render 输出「未提供诱饵嫌疑资产」占位），
        仅当构建未执行（decoys 为 None）时才算「诱饵判定清单」缺失。
        既有四项语义保持不变；Ch10 新增节在存在数据时才纳入门禁（增量追加）。
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
