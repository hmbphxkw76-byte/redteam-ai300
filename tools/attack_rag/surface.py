#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""前置：定位 RAG 攻击面（SKILL.md「前置：定位 RAG 攻击面」）。

输入是 `recon-ai` 的资产清单（七字段契约，机读 dict），本模块只做
**归类与如实标注**，不发起探测、不猜测未观测字段：

1. 组件：RAG 库 / 向量库 → 向量库类型、检索入口；
2. 下游 agent：`agent系统` 资产 → 是否消费检索结果及其能力（未知即「不可判定」）；
3. 护栏基线：`护栏` 资产 → 检索过滤 / 输出审查 / 信任边界，作为投毒效果对照。

无可读清单时退化为合成 harness 面，并在结论里标注来源，避免把假设当观测。
"""
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Sequence, Tuple

UNKNOWN = "不可判定"

RAG_CATEGORIES: Tuple[str, ...] = ("RAG库", "向量库")
AGENT_CATEGORY = "agent系统"
GUARDRAIL_CATEGORY = "护栏"

WRITABLE_VALUES: Tuple[str, ...] = ("yes", "no", "unknown")
COUPLED_VALUES: Tuple[str, ...] = ("yes", "no", "unknown")


def _assets(data: Any) -> List[Dict[str, Any]]:
    """兼容 `AssetInventory.to_dict()` 与裸资产列表两种输入。"""
    if isinstance(data, dict):
        raw = data.get("assets") or []
    elif isinstance(data, (list, tuple)):
        raw = data
    else:
        raise ValueError("资产清单须为 dict（含 assets）或资产列表")
    return [a for a in raw if isinstance(a, dict)]


def _label(asset: Dict[str, Any]) -> str:
    """资产的一行标签：产品/版本 @ 端点（凭证线索只带指纹，不落明文）。"""
    product = str(asset.get("product") or "").strip() or UNKNOWN
    version = str(asset.get("version") or "").strip()
    endpoint = str(asset.get("endpoint") or "").strip()
    text = "%s %s" % (product, version) if version else product
    if endpoint:
        text = "%s @ %s" % (text.strip(), endpoint)
    return text.strip()


def _by_category(assets: Iterable[Dict[str, Any]], category: str):
    return [a for a in assets
            if str(a.get("category") or "").strip() == category]


@dataclass(frozen=True)
class RagSurface:
    """一次定位的对外结论；`render()` 直接进证据「关键输出」。"""

    vector_db: str = ""
    retrieval: str = ""
    ingest: str = ""
    downstream: str = ""
    capabilities: Tuple[str, ...] = ()
    guardrails: Tuple[str, ...] = ()
    writable: str = "unknown"
    source: str = "synthetic"
    retrieval_mode: str = ""      # enterprise / synthetic / 不可判定
    tracing: str = ""             # Phoenix 追踪面；缺项留空由上层标注

    def identified(self) -> bool:
        """识别到 RAG 组件（有向量库或检索入口）才算定位成功。"""
        return bool(self.vector_db or self.retrieval)

    def baseline_known(self) -> bool:
        """是否记录到护栏基线（无护栏资产也是基线，但须显式标注）。"""
        return bool(self.guardrails)

    def guardrail_baseline(self) -> str:
        """护栏基线三行（SKILL.md 前置第 3 项），驱动后续「未产生影响」判定。"""
        if self.guardrails:
            found = "、".join(self.guardrails)
            filter_line = "已记录护栏资产：%s（投毒后须复核是否生效）" % found
            review_line = "已记录护栏资产：%s（观察是否拦截被操纵输出）" % found
        else:
            filter_line = "未记录护栏资产（按无检索过滤处理，须在投毒后复核）"
            review_line = "未记录护栏资产（按无输出审查处理，不得据此断言无护栏）"
        boundary = ("下游 agent 直接拼接检索上下文（据 recon agent 资产推断）"
                    if self.downstream else "信任边界%s（未识别下游 agent）" % UNKNOWN)
        return ("检索过滤: %s\n输出审查: %s\n信任边界: %s"
                % (filter_line, review_line, boundary))

    def render(self) -> str:
        return ("来源: %s\n向量库/检索入口: %s | %s\n摄取通道: %s\n"
                "下游 agent: %s\n下游能力: %s\n可写判定: %s\n"
                "检索模式: %s\n追踪面: %s\n护栏基线:\n%s"
                % (self.source, self.vector_db or UNKNOWN, self.retrieval or UNKNOWN,
                   self.ingest or UNKNOWN, self.downstream or UNKNOWN,
                   "、".join(self.capabilities) or UNKNOWN,
                   self.writable, self.retrieval_mode or UNKNOWN,
                   self.tracing or UNKNOWN, self.guardrail_baseline()))

    def as_dict(self):
        return {"source": self.source, "vector_db": self.vector_db,
                "retrieval": self.retrieval, "ingest": self.ingest,
                "downstream": self.downstream,
                "capabilities": list(self.capabilities),
                "guardrails": list(self.guardrails),
                "writable": self.writable,
                "retrieval_mode": self.retrieval_mode, "tracing": self.tracing}


def from_inventory(data: Any, ingest: str = "",
                   writable: str = "unknown") -> RagSurface:
    """从 recon-ai 资产清单归类出 RAG 攻击面；缺项留空由上层如实标注。"""
    assets = _assets(data)
    rag = _by_category(assets, RAG_CATEGORIES[0]) + _by_category(assets, RAG_CATEGORIES[1])
    agents = _by_category(assets, AGENT_CATEGORY)
    guards = _by_category(assets, GUARDRAIL_CATEGORY)

    vector_db = "；".join(_label(a) for a in rag) if rag else ""
    retrieval = next((str(a.get("endpoint") or "").strip() for a in rag
                      if str(a.get("endpoint") or "").strip()), "")
    downstream = "；".join(_label(a) for a in agents) if agents else ""
    capabilities = ()
    if agents:
        # 只陈述「清单里有 agent 且其端点可达」，具体能力未观测即不可判定。
        capabilities = ("可触达 agent 入口（具体能力%s）" % UNKNOWN,)
    guardrails = tuple(_label(a) for a in guards)
    return RagSurface(vector_db=vector_db, retrieval=retrieval, ingest=ingest,
                      downstream=downstream, capabilities=capabilities,
                      guardrails=guardrails, writable=writable, source="recon-ai 资产清单")


def synthetic(writable: str = "unknown", ingest: str = "",
              downstream: str = "合成 harness 生成器（离线）") -> RagSurface:
    """无 recon 清单时的合成面：如实标注来源，不冒充真实观测。"""
    return RagSurface(
        vector_db="synthetic-harness（本地合成向量库）",
        retrieval="in-process retrieve(k)", ingest=ingest,
        downstream=downstream,
        capabilities=("拼接检索上下文（合成面已实现）",),
        guardrails=(), writable=writable, source="synthetic（未提供 recon 清单）")


def surface_from_file(path: str, ingest: str = "",
                      writable: str = "unknown") -> RagSurface:
    """读取 recon 资产清单 JSON（`AssetInventory.to_dict()` 形态）。"""
    import json
    import os
    if not os.path.isfile(path):
        raise ValueError("recon 资产清单不存在：%s" % path)
    with open(path, encoding="utf-8") as handle:
        return from_inventory(json.load(handle), ingest=ingest, writable=writable)


def validate_flags(writable: str, coupled: str) -> Sequence[str]:
    """三值参数校验；返回错误信息列表（空即合法）。"""
    problems = []
    if writable not in WRITABLE_VALUES:
        problems.append("rag_writable 取值非法：%s（允许 %s）"
                        % (writable, "/".join(WRITABLE_VALUES)))
    if coupled not in COUPLED_VALUES:
        problems.append("downstream_coupled 取值非法：%s（允许 %s）"
                        % (coupled, "/".join(COUPLED_VALUES)))
    return problems
