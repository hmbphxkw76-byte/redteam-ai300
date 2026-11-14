#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""recon-ai 领域模型（纯数据，无外部依赖）。

本模块是「AI 资产 / 资产清单 / 证据引用」类型与契约字段的唯一定义处。
其他模块只 import 本模块，本模块不 import 任何本项目模块 → 依赖图无环。
"""
import hashlib
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import List

# 资产清单契约（SKILL.md 校验标准 / AC-13）：七字段，缺任一即清单不合规
ASSET_FIELDS = (
    "asset_id",       # 资产ID：稳定唯一标识，如 ai-llm-<host>-01
    "category",       # 组件类别
    "product",        # 产品/引擎
    "version",        # 版本或版本区间
    "endpoint",       # 暴露端点/端口
    "credential_hint",  # 凭证线索（仅指纹，不落盘明文）
    "evidence_step",  # 关联证据片段 step_id
)

UNKNOWN = "不可判定"


class Existence(str, Enum):
    """资产存在性三值判定（AC-04）。布尔不足以表达「未发现 ≠ 不存在」。"""

    PRESENT = "存在"
    ABSENT = "不存在"
    UNDETERMINED = UNKNOWN


class Category(str, Enum):
    """7 类 AI 组件（与 SKILL.md 的 recon-01..07 一一对应）。"""

    LLM_ENGINE = "LLM引擎"
    MODEL_SERVICE = "模型服务"
    RAG = "RAG库"
    VECTOR_DB = "向量库"
    AGENT = "agent系统"
    MCP = "MCP工具面"
    GUARDRAIL = "护栏"


def credential_hint(secret):
    """把凭据线索压缩为指纹（SKILL.md OPSEC：不写盘明文）。

    返回 `Bearer-<前8位哈希>` 形态；空值返回空串。
    """
    if not secret:
        return ""
    digest = hashlib.sha256(str(secret).encode("utf-8")).hexdigest()[:8]
    return "Bearer-%s" % digest


@dataclass
class ProbeResult:
    """一次探测请求的可观测结果（外部行为，不含实现细节）。"""

    step_id: str
    url: str
    method: str = "GET"
    status: int = 0
    content_type: str = ""
    body: str = ""
    headers: dict = field(default_factory=dict)
    existence: Existence = Existence.UNDETERMINED
    signature: str = ""
    note: str = ""
    command: str = ""
    request_body: dict = field(default_factory=dict)
    elapsed_ms: int = 0
    error: str = ""

    @property
    def ok(self):
        """2xx 且无网络层错误。"""
        return not self.error and 200 <= self.status < 300

    @property
    def text(self):
        """用于指纹匹配的文本面：响应体 + 关键响应头。"""
        return "%s\n%s\n%s" % (self.content_type, self.body, self.headers)

    def brief(self, limit=800):
        """证据片段用的关键输出摘要（避免单步输出无界增长，C4）。"""
        if self.error:
            return "%s %s → ERROR: %s" % (self.method, self.url, self.error)
        body = self.body if len(self.body) <= limit else (
            self.body[:limit] + "\n…（已截断：完整响应 %d 字节，命令可原样重跑取全文）"
            % len(self.body))
        return "%s %s → HTTP %d\n%s" % (self.method, self.url, self.status, body)


@dataclass
class Asset:
    """资产清单中的一条资产（七字段契约）。"""

    asset_id: str
    category: str
    product: str
    version: str
    endpoint: str
    credential_hint: str
    evidence_step: str
    phase: str = ""      # 可选附加字段（不在七字段契约内）：编排阶段标识

    def missing_fields(self):
        """返回缺失或占位为空的契约字段名列表（AC-13）。"""
        out = []
        for name in ASSET_FIELDS:
            value = getattr(self, name, "")
            if value is None or not str(value).strip():
                out.append(name)
        return out

    def to_dict(self):
        data = {name: getattr(self, name) for name in ASSET_FIELDS}
        if self.phase:
            data["phase"] = self.phase
        return data


@dataclass
class AssetInventory:
    """结构化资产清单（人类可读 + 机读双态，AC-14）。"""

    target: str
    profile: str
    generated_at: str
    assets: List[Asset] = field(default_factory=list)
    decoy_suspected: bool = False
    decoy_reason: str = ""
    timebox_minutes: int = 30
    failed_steps: List[str] = field(default_factory=list)
    undetermined: List[str] = field(default_factory=list)

    @classmethod
    def create(cls, target, profile, assets=None, **kwargs):
        return cls(
            target=target,
            profile=profile,
            generated_at=datetime.now().astimezone().isoformat(timespec="seconds"),
            assets=list(assets or []),
            **kwargs
        )

    def contract_violations(self):
        """返回契约违规描述列表；空列表即合规（AC-13）。"""
        problems = []
        if not self.assets:
            problems.append("资产清单为空：未产出任何资产（应至少记录不可判定类别）")
        seen = set()
        for asset in self.assets:
            miss = asset.missing_fields()
            if miss:
                problems.append("%s 缺字段：%s" % (asset.asset_id or "（无ID）", "、".join(miss)))
            if asset.asset_id in seen:
                problems.append("资产ID 重复：%s" % asset.asset_id)
            seen.add(asset.asset_id)
        return problems

    def to_dict(self):
        return {
            "target": self.target,
            "profile": self.profile,
            "generated_at": self.generated_at,
            "timestamp": self.generated_at,
            "decoy_suspected": self.decoy_suspected,
            "decoy_reason": self.decoy_reason,
            "timebox_minutes": self.timebox_minutes,
            "failed_steps": list(self.failed_steps),
            "undetermined": list(self.undetermined),
            "assets": [a.to_dict() for a in self.assets],
        }

    def to_markdown(self):
        """人类可读形态：清单表 + 判定摘要。"""
        lines = [
            "# AI 资产清单（recon-ai）",
            "",
            "- **目标**：`%s`" % self.target,
            "- **执行分级**：`%s`" % self.profile,
            "- **生成时间**：`%s`" % self.generated_at,
            "- **资产条目**：%d" % len(self.assets),
            "- **疑似诱饵**：%s%s" % (
                "是" if self.decoy_suspected else "否",
                ("（%s）" % self.decoy_reason) if self.decoy_reason else ""),
            "",
            "| 资产ID | 组件类别 | 产品/引擎 | 版本 | 暴露端点/端口 | 凭证线索 | 关联证据 step_id |",
            "|---|---|---|---|---|---|---|",
        ]
        for a in self.assets:
            lines.append("| `%s` | %s | %s | %s | `%s` | %s | `%s` |" % (
                a.asset_id, a.category, a.product, a.version, a.endpoint,
                a.credential_hint or "无", a.evidence_step))
        if self.undetermined:
            lines += ["", "**不可判定类别**（需主动探测或人工确认）：%s" % "、".join(self.undetermined)]
        if self.failed_steps:
            lines += ["", "**失败步骤**（失败隔离，不阻塞其余枚举）：%s" % "、".join(self.failed_steps)]
        lines += ["", "> 复现：`python tools/recon_ai/cli.py run --target %s --profile %s`"
                  % (self.target, self.profile)]
        return "\n".join(lines) + "\n"
