#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""指纹识别：响应签名 → 产品/版本/组件类别。

规则表是本模块的唯一数据；新增组件特征只加一条规则，不改调度逻辑。
每个命中保留 `signature`（命中的原文片段），使结论可回溯、可复核。
"""
import re
from dataclasses import dataclass
from typing import List, Optional

from .model import Category

VERSION_RE = re.compile(r"([0-9]+(?:\.[0-9]+)+)")


@dataclass(frozen=True)
class Rule:
    """一条指纹规则。`product_group=0` 表示产品名取规则名（静态产品）。"""

    name: str
    pattern: str
    product: str
    category: Optional[Category]
    scope: str = "body"          # body | headers | content_type
    product_group: int = 0       # >0 时取该正则组的文本作为产品名
    flags: int = re.I


@dataclass(frozen=True)
class Match:
    """一次命中：规则名 + 产品 + 版本 + 类别 + 原文片段。"""

    rule: str
    product: str
    version: str
    category: Optional[Category]
    signature: str


RULES = (
    # 部署配置泄露默认模型 → LLM 引擎类别（版本从产品名中提取，如 LongCat-2.5）
    Rule("model_default", r'"llm_model_default"\s*:\s*"([^"]+)"',
         "模型默认值", Category.LLM_ENGINE, product_group=1),
    # FastAPI 的 404 语义
    Rule("fastapi_404", r'\{"detail"\s*:\s*"Not Found"\}',
         "FastAPI", Category.MODEL_SERVICE),
    # Pydantic 校验错误（422）暴露参数名与类型
    Rule("pydantic_422", r'"loc"\s*:\s*\[', "FastAPI+Pydantic",
         Category.MODEL_SERVICE, flags=0),
    # SSE 元数据事件 → 流式聊天面
    Rule("sse_meta", r"event:\s*meta", "SSE 流式聊天面",
         Category.MODEL_SERVICE, flags=0),
    Rule("sse_content", r'"content"\s*:\s*"', "SSE 流式聊天面",
         Category.MODEL_SERVICE, flags=0),
    # 检索链路痕迹 → RAG
    Rule("rag_trace", r"(retriev\w*|knowledge|embedding|vector\w*|documents)",
         "RAG 检索链路（痕迹）", Category.RAG),
    # MCP 痕迹（限定 token，避免 "tool" 泛匹配）
    Rule("mcp_trace", r"(\bmcp\w*\b|\"tools\"\s*:)", "MCP 服务面",
         Category.MCP),
    # 凭据校验预言机：成功/失败均返 200 + success 布尔
    Rule("secret_oracle", r'"success"\s*:\s*(?:true|false)', "凭据校验预言机",
         Category.MCP, flags=0),
    # 反代标识（基础设施指纹，仅入注记，不单独建资产）
    Rule("nginx", r"nginx/([0-9]+\.[0-9]+\.[0-9]+)", "nginx", None,
         scope="headers"),
)


def _scope_text(result, scope):
    if scope == "headers":
        return "\n".join("%s: %s" % (k, v) for k, v in (result.headers or {}).items())
    if scope == "content_type":
        return result.content_type or ""
    return result.body or ""


def _version_of(text):
    m = VERSION_RE.search(text or "")
    return m.group(1) if m else ""


def detect(result) -> List[Match]:
    """对一次探测结果应用全部规则，返回命中列表（保序、去重）。"""
    out, seen = [], set()
    for rule in RULES:
        text = _scope_text(result, rule.scope)
        if not text:
            continue
        m = re.search(rule.pattern, text, rule.flags)
        if not m:
            continue
        if rule.product_group and m.lastindex and m.lastindex >= rule.product_group:
            product = m.group(rule.product_group).strip()
        else:
            product = rule.product
        key = (rule.name, product)
        if key in seen:
            continue
        seen.add(key)
        version = _version_of(product) or (
            m.group(1) if (rule.product_group and m.lastindex and
                           m.group(1) != product) else "")
        out.append(Match(rule=rule.name, product=product, version=version,
                         category=rule.category,
                         signature=m.group(0)[:160]))
    return out


def primary(result, category=None) -> Optional[Match]:
    """取指定类别的首个命中（未指定类别则取首个带类别的命中）。"""
    for match in detect(result):
        if match.category is None:
            continue
        if category is None or match.category == category:
            return match
    return None
