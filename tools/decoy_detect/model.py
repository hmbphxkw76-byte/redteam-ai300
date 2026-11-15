#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""decoy-detect 领域模型（纯数据，零外部依赖）。

本模块是「疑似诱饵主机信号 / 诱饵判定」类型与五字段契约的唯一定义处。
其他模块只 import 本模块，本模块不 import 本包任何模块 → 依赖图无环。

五字段契约（SKILL.md 质量门 / v2 AC7）：主机标识 + 命中维度 + 具体依据 +
放弃理由 + 时间戳，缺任一即判定清单不合规。
"""
import json
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional

# 诱饵判定清单五字段（顺序即 markdown 列序）
JUDGMENT_FIELDS = ("host_id", "hit_dimensions", "evidence",
                   "abandonment_reason", "timestamp")


class Dimension(str, Enum):
    """三维度特征（SKILL.md 第 1 节 / GLOSSARY「三维度特征」）。"""

    BEHAVIOR = "行为特征"       # 无 AI 基础设施面
    LEAK_MISSING = "漏洞缺失"   # 无高价值服务/无可达入口/无可利用配置错误
    NO_VALUE = "无价值特征"     # 枚举过干净/信息缺失/与资产清单严重不符


class JudgmentConclusion(str, Enum):
    """判定结论（SKILL.md 第 3 节：两种结论不混淆）。"""

    DECOY = "诱饵"
    UNCERTAIN_ABANDONED = "不确定-已放弃"
    SCORED = "计分目标"          # 非清单条目（判定的补集）


@dataclass
class HostSignals:
    """单台主机的可机读判定信号（外部可观测，不含实现细节）。"""

    host_id: str
    ai_surface_present: bool = True      # 行为特征：是否具备 AI 基础设施面
    high_value_service: bool = True      # 漏洞缺失：是否存在高价值服务
    reachable_entry: bool = True         # 漏洞缺失：是否存在可达入口
    exploitable_misconfig: bool = True   # 漏洞缺失：是否存在可利用配置错误
    banner_service_count: int = 1        # 无价值：枚举观察到的 banner/服务数
    info_sufficient: bool = True         # 无价值：信息是否足够定位资产
    inventory_match: bool = True         # 无价值：是否与资产清单描述相符
    decoy_suspected: bool = False        # recon-ai 单主机初判（复用信号，C1）
    decoy_reason: str = ""
    notes: str = ""


@dataclass
class DecoyJudgment:
    """诱饵判定清单的一条（五字段契约）。"""

    host_id: str
    hit_dimensions: List[Dimension] = field(default_factory=list)
    evidence: Dict[str, str] = field(default_factory=dict)   # 维度值 -> 具体依据
    abandonment_reason: str = ""
    conclusion: JudgmentConclusion = JudgmentConclusion.SCORED
    timestamp: str = ""
    elapsed_seconds: float = 0.0
    timebox_exceeded: bool = False
    cross_validated: bool = False

    def missing_fields(self) -> List[str]:
        """返回缺失的五字段名列表；空列表即合规（v2 AC7/AC8）。"""
        problems = []
        if not (self.host_id or "").strip():
            problems.append("host_id")
        if not self.hit_dimensions:
            problems.append("hit_dimensions")
        if not self.evidence:
            problems.append("evidence")
        if not (self.abandonment_reason or "").strip():
            problems.append("abandonment_reason")
        if not (self.timestamp or "").strip():
            problems.append("timestamp")
        return problems

    def dimension_values(self) -> List[str]:
        return [d.value for d in self.hit_dimensions]

    def to_dict(self) -> dict:
        return {
            "host_id": self.host_id,
            "hit_dimensions": self.dimension_values(),
            "evidence": dict(self.evidence),
            "abandonment_reason": self.abandonment_reason,
            "conclusion": self.conclusion.value,
            "timestamp": self.timestamp,
            "elapsed_seconds": round(self.elapsed_seconds, 1),
            "timebox_exceeded": self.timebox_exceeded,
            "cross_validated": self.cross_validated,
        }


@dataclass
class ScanInput:
    """一次诱饵判定的输入：多主机信号集合 + 预期诱饵数（≈2）。"""

    expected_decoys: int = 2
    hosts: List[dict] = field(default_factory=list)
    raw: dict = field(default_factory=dict)


def now_iso() -> str:
    """本地时区 ISO 时间戳（秒级，与证据片段一致）。"""
    return datetime.now().astimezone().isoformat(timespec="seconds")


def load_scan(path: str) -> ScanInput:
    """读取诱饵判定输入 JSON。

    期望形态（见 docs/operations/decoy-detect-design.md §3）::

        {
          "expected_decoys": 2,
          "hosts": [
            {"host_id": "...", "decoy_suspected": true, "present_categories": [],
             "high_value_service": false, "reachable_entry": false,
             "exploitable_misconfig": false, "banner_service_count": 0,
             "info_sufficient": false, "inventory_match": false,
             "elapsed_seconds": 900, "threat_model_decoy": true}
          ]
        }

    文件缺失/JSON 非法/结构不符 → ValueError（CLI 转退出码 2）。
    """
    try:
        with open(path, "r", encoding="utf-8") as handle:
            data = json.load(handle)
    except OSError as exc:
        raise ValueError("无法读取输入：%s" % exc)
    except ValueError as exc:
        raise ValueError("输入不是合法 JSON：%s" % exc)
    if not isinstance(data, dict):
        raise ValueError("输入顶层须为对象（含 hosts 列表）")
    hosts = data.get("hosts")
    if not isinstance(hosts, list) or not hosts:
        raise ValueError("输入缺少非空 hosts 列表")
    try:
        expected = int(data.get("expected_decoys", 2))
    except (TypeError, ValueError):
        raise ValueError("expected_decoys 须为整数")
    return ScanInput(expected_decoys=expected, hosts=hosts, raw=data)


def coerce_host(value: Optional[dict]) -> dict:
    """把一条主机记录归一为 dict（容忍缺省）。"""
    return value if isinstance(value, dict) else {}
