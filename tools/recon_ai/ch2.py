#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Ch2 对齐的旁路侦察分析层（离线、零网络）。

事实来源：OffSec AI-300《Reconnaissance for AI Targets》§2.1–2.4。
本模块把文档中的分层枚举分类法、模型行为指纹、RAG 源元数据、
诱饵识别与检测规避规则固化为可复用纯函数；只消费调用方提供的观测数据，
不发起请求、不把产品文档当运行时事实、不输出明文凭据。

公开接口：
  TAXONOMY / classify_endpoint_status / parse_ai_headers / parse_health_config
  fingerprint_behavior / parse_rag_sources / map_knowledge_base
  classify_disclosure / detect_canary / DETECTION_RULES
  assess_detection / covert_rewrite / pacing_plan / mine_repository
  parse_self_describing / parse_response_metadata / parse_client_js
  probe_threshold_series / assess_log_visibility / parse_shadow_endpoints
  analyze / validate_analysis
"""
import json
import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List

from . import shadow
from .model import Existence, credential_hint

# §2.1 分层枚举属性分类法：文档四层 → 现有 7 步组件类别（C1 单一事实源）
TAXONOMY = (
    ("模型层", ("recon-01", "recon-02"),
     "模型身份 / 能力边界 / 训练数据特征 / 行为约束"),
    ("RAG 层", ("recon-03", "recon-04"),
     "嵌入模型 / 向量库 / 分块参数 / 检索阈值 / 文档源"),
    ("Agent 与工具层", ("recon-05", "recon-06"),
     "工具与 schema / 权限边界 / 编排逻辑 / 错误处理"),
    ("基础设施与护栏", ("recon-07",),
     "API 端点 / 限流 / 错误格式 / 后端服务身份 / 护栏"),
)

AI_HEADER_RULES = (
    ("X-AI-Backend", "LLM引擎", "AI 后端自报", "高"),
    ("X-RAG-Provider", "RAG", "RAG 提供方自报", "高"),
    ("X-Powered-By", "基础设施", "应用框架自报", "中"),
    ("Server", "基础设施", "服务端自报", "中"),
    ("Via", "基础设施", "代理链自报", "中"),
)

HEALTH_FIELDS = ("model", "mcp_enabled", "rag_enabled", "version", "service", "status")

BEHAVIOR_TECHNIQUES = ("identity", "contradiction", "cutoff", "style",
                       "capability", "context")

FAMILY_HINTS = (
    ("qwen", "Qwen"), ("alibaba cloud", "Qwen"), ("meta ai", "Llama"),
    ("llama", "Llama"), ("anthropic", "Claude"), ("claude", "Claude"),
    ("openai", "GPT"), ("gpt-4", "GPT"), ("mistral", "Mistral"),
    ("gemma", "Gemma"),
)

CANARY_MARKERS = ("HONEYPOT", "CANARY", "DECOY")
PREDICTABLE_SECRET = re.compile(r"\b[A-Z][A-Za-z]+20\d{2}!?\b")
INTERNAL_URL = re.compile(
    r"https?://[^\s\"']+\.(?:internal|local)\b|https?://(?:localhost|127\.0\.0\.1)\b",
    re.I)
CREDENTIAL_CONTEXT = re.compile(
    r"(?:key|password|secret|token)[^\n]{0,40}(?:HONEYPOT|CANARY|TEST|DECOY)", re.I)

DETECTION_RULES = (
    ("E01", "文档源枚举", ("what documents", "what sources",
                       "list documents", "list sources")),
    ("E02", "敏感主题", ("confidential", "salary", "strategic plan")),
    ("E03", "休假策略", ("pto", "time off", "leave policy")),
    ("E04", "提示词提取", ("system prompt", "your instructions")),
    ("D03", "身份探测", ("what model are you", "who created you",
                      "knowledge cutoff")),
)

D02_AI_PATHS = ("/api/chat", "/api/generate", "/v1/completions",
                "/api/embeddings", "/v1/chat/completions")

# §2.1 自描述协议：MCP 以 JSON-RPC 暴露 tool schema；A2A 暴露能力与信任关系。
SELF_DESCRIBE_FIELDS = ("tools", "capabilities", "skills", "parameters",
                        "return_type", "trust_relationships", "delegation")
# §2.3 客户端配置键（JS 工件）：apiBase / assistantEndpoint / featureFlags。
CLIENT_CONFIG_KEYS = ("apiBase", "assistantEndpoint", "apiEndpoint", "baseUrl",
                      "featureFlags", "enableAI", "debugMode", "timeout")
# §2.4 交互日志字段： defenders 可见 query/answer/sources，缺语义/意图/跨会话关联。
LOG_FIELDS = ("query", "answer", "sources", "session_id", "timestamp")
LOG_GAPS = ("semantic_analysis", "prompt_injection_detection",
            "intent_classification", "cross_session_correlation")
# §2.3 检索阈值递减序列：exact → synonym → misspelling。
THRESHOLD_STAGES = ("exact", "synonym", "misspelling")


@dataclass
class Signal:
    """一条可复核信号：值 + 依据 + 置信度；值不含明文凭据。"""

    kind: str
    value: str
    basis: str
    confidence: str = "中"

    def to_dict(self):
        return {"kind": self.kind, "value": self.value,
                "basis": self.basis, "confidence": self.confidence}


@dataclass
class Finding:
    """一类分析结论：判定 + 信号列表 + 注记（依据独立于原始输出）。"""

    name: str
    verdict: str = Existence.UNDETERMINED.value
    signals: List[Signal] = field(default_factory=list)
    note: str = ""

    family: str = ""

    def to_dict(self):
        return {"name": self.name, "verdict": self.verdict,
                "signals": [s.to_dict() for s in self.signals],
                "note": self.note, "family": self.family}


def classify_endpoint_status(status):
    """§2.3 401 vs 404：401/403=存在需认证；404=不存在；2xx=存在；其余不可判定。"""
    if status in (401, 403):
        return "AUTH_REQUIRED"
    if status == 404:
        return "ABSENT"
    if isinstance(status, int) and 200 <= status < 300:
        return "PRESENT"
    return "UNDETERMINED"


def parse_ai_headers(headers):
    """§2.2 从响应头抽 AI 专用指纹；仅认实际观测到的头，不推断。"""
    out = []
    for name, category, label, conf in AI_HEADER_RULES:
        for key, value in (headers or {}).items():
            if str(key).lower() == name.lower():
                out.append(Signal("header:%s" % name, str(value)[:200],
                                  "%s（%s，%s 层）" % (label, name, category), conf))
    for key, value in (headers or {}).items():
        if str(key).lower().startswith("x-kong-") or \
                str(key).lower() in ("ratelimit-limit", "ratelimit-remaining"):
            out.append(Signal("header:%s" % key, str(value)[:120],
                              "网关/限流自报（§2.3 Kong 指纹）", "中"))
    return out


def parse_health_config(body):
    """§2.2 健康端点配置泄露；须含 status 或 model 才认定，避免普通 JSON 误报。"""
    if not body:
        return []
    try:
        data = json.loads(body)
    except (TypeError, ValueError):
        return []
    if not isinstance(data, dict) or not ({"status", "model"} & set(data)):
        return []
    return [Signal("health:%s" % key, json.dumps(data[key], ensure_ascii=False)[:160],
                   "健康端点字段 %s" % key, "高")
            for key in HEALTH_FIELDS if key in data]


def _family_of(text):
    low = (text or "").lower()
    for needle, family in FAMILY_HINTS:
        if needle in low:
            return family
    return ""


def fingerprint_behavior(observations):
    """§2.3 六类行为指纹；多技术一致才下家族结论，单信号不得定论。"""
    signals, families = [], []
    for obs in observations or []:
        technique = str(obs.get("technique") or "").lower()
        response = str(obs.get("response") or "")
        probe = str(obs.get("probe") or "")
        if technique not in BEHAVIOR_TECHNIQUES:
            continue
        if not response and technique != "context":
            continue
        if technique == "identity":
            family = _family_of(response)
            if family:
                families.append(family)
                signals.append(Signal("behavior:identity", family,
                                      "直接身份探测回显（%s）" % probe[:80], "高"))
        elif technique == "contradiction":
            if re.search(r"correct|clarify|actually|not\s+.{0,24}(openai|anthropic|gpt)",
                         response, re.I):
                family = _family_of(response)
                if family:
                    families.append(family)
                    signals.append(Signal("behavior:contradiction", family,
                                          "错误归因被自纠（%s）" % probe[:80], "高"))
        elif technique == "cutoff":
            match = re.search(r"(?:cutoff|截至|训练数据)[^\n]{0,80}", response, re.I)
            if match:
                signals.append(Signal("behavior:cutoff", match.group(0)[:100],
                                      "知识截止自报须用事件探测复核", "中"))
        elif technique == "style":
            markers = []
            if '"""' in response or "'''" in response:
                markers.append("docstring")
            if re.search(r"example|示例|usage", response, re.I):
                markers.append("示例注释")
            if re.search(r"edge case|边界|except", response, re.I):
                markers.append("边界处理")
            if markers:
                signals.append(Signal("behavior:style", "、".join(markers),
                                      "响应风格特征（%d 项）" % len(markers), "低"))
        elif technique == "capability":
            expected = str(obs.get("expected") or "").strip()
            if expected:
                ok = expected.lower() in response.lower()
                signals.append(Signal("behavior:capability",
                                      "正确" if ok else "偏差",
                                      "预期值 %s 与回显比对" % expected[:40], "中"))
        elif technique == "context":
            marker = str(obs.get("marker") or "")
            recalled = obs.get("recalled")
            if marker and isinstance(recalled, bool):
                signals.append(Signal("behavior:context",
                                      "保留" if recalled else "丢失",
                                      "标记 %s 在填充后%s" % (marker[:24],
                                                          "可回忆" if recalled else "不可回忆"),
                                      "中"))
    verdict = Existence.PRESENT.value if signals else Existence.UNDETERMINED.value
    note = "六类技术观测 %d 项" % len(signals)
    family_concluded = ""
    if families:
        top = max(set(families), key=families.count)
        if families.count(top) >= 2:
            family_concluded = top
            note += "；多信号一致指向 %s" % top
        else:
            note += "；单信号指向 %s，未定家族（须组合其它技术）" % top
    finding = Finding("模型行为指纹", verdict, signals, note)
    finding.family = family_concluded  # 仅多信号一致时置位，供校验器判定
    return finding


def parse_rag_sources(body):
    """§2.3 解析 sources[] 元数据：文档名 / chunk / 原文 / 相似度分数。"""
    try:
        data = json.loads(body)
    except (TypeError, ValueError):
        return []
    if not isinstance(data, dict):
        return []
    sources = data.get("sources")
    if not isinstance(sources, list):
        return []
    out = []
    for source in sources:
        if not isinstance(source, dict):
            continue
        group = []
        for key in ("title", "chunk_id", "text", "vector_score",
                    "bm25_score", "combined_score"):
            if key in source:
                value = str(source[key])
                if key == "text":
                    value = value[:200] + ("…" if len(value) > 200 else "")
                group.append(Signal("source:%s" % key, value,
                                    "RAG 源元数据 %s" % key,
                                    "中" if key == "text" else "高"))
        if group:
            out.append(group)
    return out


def map_knowledge_base(source_groups):
    """§2.3 知识库映射 / chunk 边界 / 阈值观察（只汇总已解析的源元数据）。"""
    titles, chunk_ids, scores = set(), [], []
    for group in source_groups or []:
        for signal in group:
            if signal.kind == "source:title":
                titles.add(signal.value)
            elif signal.kind == "source:chunk_id":
                match = re.search(r"(\d+)", signal.value)
                if match:
                    chunk_ids.append(int(match.group(1)))
            elif signal.kind in ("source:vector_score", "source:combined_score"):
                try:
                    scores.append(float(signal.value))
                except ValueError:
                    pass
    signals = []
    if titles:
        signals.append(Signal("kb:documents", "、".join(sorted(titles)[:12]),
                              "跨查询累计文档名（§2.3 知识库映射）", "高"))
    if chunk_ids:
        signals.append(Signal("kb:chunk_range", "%d–%d" % (min(chunk_ids), max(chunk_ids)),
                              "chunk_id 范围提示分块粒度与文档规模", "中"))
    if scores:
        signals.append(Signal("kb:score_range", "%.2f–%.2f" % (min(scores), max(scores)),
                              "相似度分布提示检索阈值（须多查询复核）", "中"))
    return Finding("RAG 知识库映射",
                   Existence.PRESENT.value if signals else Existence.UNDETERMINED.value,
                   signals, "源元数据 %d 组" % len(source_groups or []))


def classify_disclosure(source):
    """§2.3 详细度分级：minimal / moderate / detailed / none。"""
    if not isinstance(source, dict):
        return "none"
    keys = set(source)
    if {"title", "chunk_id", "text"} <= keys and (
            {"vector_score", "bm25_score", "combined_score"} & keys):
        return "detailed"
    if "title" in keys and "text" in keys:
        return "moderate"
    if "title" in keys:
        return "minimal"
    return "none"


def detect_canary(text):
    """§2.4 诱饵识别：显式标记 / 可预测凭据 / 不可解析内部域 / 信息过完整。"""
    raw = text or ""
    signals = []
    for marker in CANARY_MARKERS:
        if marker in raw.upper():
            signals.append(Signal("canary:marker", marker,
                                  "凭据/链接含显式诱饵标记 %s" % marker, "高"))
    if CREDENTIAL_CONTEXT.search(raw):
        signals.append(Signal("canary:context", "凭据上下文含诱饵词",
                              "密钥/口令邻近出现诱饵标记", "高"))
    for secret in PREDICTABLE_SECRET.findall(raw)[:3]:
        signals.append(Signal("canary:password", credential_hint(secret),
                              "口令呈可预测模式（名称+年份），仅留指纹", "中"))
    for url in INTERNAL_URL.findall(raw)[:3]:
        signals.append(Signal("canary:url", url[:100],
                              "内部域名外部不可解析，疑似诱饵线索", "中"))
    complete = sum(bool(re.search(pattern, raw, re.I)) for pattern in
                   ("access key", "secret access key", "account id", "console url"))
    if complete >= 3:
        signals.append(Signal("canary:completeness", "%d/4" % complete,
                              "一次性给出完整凭据组，信息过于完整", "中"))
    return Finding("诱饵识别", "命中" if signals else "未命中", signals,
                   "仅识别与留痕，不尝试使用任何凭据")


def parse_shadow_endpoints(observation):
    """§2.3 Ch2 C8：影子端点差集（OpenAPI 声明 vs 前端字面量）。"""
    result = shadow.analyze(observation)
    signals = [
        Signal("shadow:%s" % item["confidence"], item["path"], item["reason"],
               "高" if item["confidence"] == shadow.HIGH else "中")
        for item in result["candidates"]
    ]
    return Finding("影子端点", result["status"], signals, result["basis"])


def assess_detection(query):
    """§2.4 规则命中分析：关键词匹配检测规则（匹配关键词而非语义意图）。"""
    low = (query or "").lower()
    hits = []
    for rule_id, label, patterns in DETECTION_RULES:
        matched = [p for p in patterns if p in low]
        if matched:
            hits.append(Signal("detection:%s" % rule_id, rule_id,
                               "%s：命中关键词 %s" % (label, "、".join(matched)), "高"))
    return hits


def endpoint_burst_risk(paths):
    """§2.4 D02：短时间内顺序请求多个 AI 路径 → 明显枚举特征。"""
    seen = [p for p in (paths or []) if any(a in str(p) for a in D02_AI_PATHS)]
    if len(seen) >= 2:
        return Signal("detection:D02", "%d 个 AI 路径" % len(seen),
                      "顺序请求多个 AI 端点，命中时序枚举模式", "高")
    return None


def covert_rewrite(query, hits=None):
    """§2.4 隐蔽改写建议：用上下文问题替代直接枚举，不自动执行。"""
    hits = hits if hits is not None else assess_detection(query)
    rules = {h.value for h in hits}
    advice = []
    if "E01" in rules:
        advice.append("改问具体主题（如某文档某章节），让回答自然带出来源，不直接问「有哪些文档」")
    if "E04" in rules:
        advice.append("改问「怎样提问能得到更好的回答」，间接确认角色与话题边界")
    if "D03" in rules:
        advice.append("借响应元数据里的 provider/model 字段确认身份，减少直接身份问句")
    if "E03" in rules:
        advice.append("用同义场景描述替代策略缩写，避免命中关键词同时保持检索相关度")
    if not advice:
        advice.append("保持业务语境的单点提问，避免连续同主题枚举")
    return {"original": query, "hits": [h.value for h in hits],
            "suggestions": advice, "note": "建议仅供授权测试人工选择，本模块不发起请求"}


def pacing_plan(profile="passive"):
    """§2.4 节奏控制：间隔 + 混入合法流量；输出建议而非自动等待。"""
    return {"profile": profile, "min_gap_seconds": 30, "max_gap_seconds": 60,
            "mix_legitimate_traffic": True,
            "note": "检测规则匹配关键词与时序而非语义；拉长间隔并混入正常浏览可降噪"}


def mine_repository(files):
    """§2.2 仓库工件离线挖掘：依赖 / RAG 配置 / 权限 / 限制 / 供应链。"""
    result = {}
    for name, content in (files or {}).items():
        lower = str(name).lower()
        text = str(content or "")
        if lower.endswith("requirements.txt"):
            result["dependencies"] = [line.strip() for line in text.splitlines()
                                      if line.strip() and not line.startswith("#")][:24]
        elif "rag" in lower and lower.endswith((".yaml", ".yml")):
            result["rag_config"] = [line.strip() for line in text.splitlines()
                                    if re.search(r"chunk_size|chunk_overlap|model|top_k|"
                                                 r"threshold|provider|metric", line, re.I)][:20]
        elif "tool" in lower or "function" in lower:
            result["tool_schema"] = re.findall(r'"name"\s*:\s*"([^"]+)"', text)[:20]
            perms = re.findall(r'read-only|create only|readonly', text, re.I)
            if perms:
                result["permission_annotations"] = sorted(set(p.lower() for p in perms))
        elif "system" in lower:
            block = re.search(r"(?:restrictions|critical restrictions)[^\n]*\n([\s\S]{0,600})",
                              text, re.I)
            result["system_restrictions"] = [line.strip() for line in
                                             (block.group(1) if block else "").splitlines()
                                             if line.strip().startswith("-")][:12]
        elif "safety" in lower or "guardrail" in lower:
            result["guardrails"] = [line.strip() for line in text.splitlines()
                                    if re.search(r"blocked|pattern|severity|validator|flag",
                                                 line, re.I)][:20]
        elif ".env" in lower:
            result["env_keys"] = re.findall(r"^([A-Z][A-Z0-9_]+)=", text, re.M)[:20]
        elif "model" in lower and lower.endswith((".yaml", ".yml")):
            result["model_supply_chain"] = [line.strip() for line in text.splitlines()
                                            if re.search(r"model_id|quantization|gpu|"
                                                         r"inference_server|max_model_len",
                                                         line, re.I)][:16]
        elif "log" in lower or "commit" in lower:
            result["history"] = [line.strip() for line in text.splitlines()
                                 if re.search(r"commit|migrat|incident|CVE", line, re.I)][:12]
    return result


def parse_self_describing(doc):
    """§2.1 自描述协议：MCP tool schema 与 A2A 能力/信任关系（自报，须复核）。

    只消费调用方提供的 schema JSON 文本；不把自报能力当运行时事实。
    """
    if not doc:
        return Finding("自描述协议面", Existence.UNDETERMINED.value, [], "无 schema 观测")
    try:
        data = json.loads(doc) if isinstance(doc, str) else doc
    except (TypeError, ValueError):
        return Finding("自描述协议面", Existence.UNDETERMINED.value, [], "schema 非 JSON")
    if not isinstance(data, dict):
        return Finding("自描述协议面", Existence.UNDETERMINED.value, [], "schema 非对象")
    signals = []
    proto = str(data.get("protocol", "")).upper()
    tools = data.get("tools")
    if isinstance(tools, list):
        for tool in tools[:20]:
            name = tool.get("name") if isinstance(tool, dict) else str(tool)
            if name:
                signals.append(Signal("self:tool", str(name)[:80],
                                      "工具自描述 name（%s）" % (proto or "MCP"), "高"))
    for key in SELF_DESCRIBE_FIELDS:
        if key in data and key != "tools":
            value = json.dumps(data[key], ensure_ascii=False)[:160]
            signals.append(Signal("self:%s" % key, value,
                                  "自描述字段 %s（%s，须运行时复核）" % (key, proto or "MCP"), "中"))
    if proto == "A2A":
        signals.append(Signal("self:protocol", "A2A",
                              "A2A 端点暴露能力与信任关系（§2.1）", "高"))
    return Finding("自描述协议面",
                   Existence.PRESENT.value if signals else Existence.UNDETERMINED.value,
                   signals, "%s schema 字段 %d 项" % (proto or "MCP", len(signals)))


def parse_response_metadata(body):
    """§2.4 metadata 泄露：从聊天响应体抽 provider/model（wrapper 回传上游对象）。

    小模型（1B）自纠能力弱，metadata 泄露是更可靠的指纹向量。仅认实际字段。
    """
    if not body:
        return []
    try:
        data = json.loads(body) if isinstance(body, str) else body
    except (TypeError, ValueError):
        return []
    if not isinstance(data, dict):
        return []
    out = []
    for container in (data, data.get("metadata"), data.get("meta")):
        if not isinstance(container, dict):
            continue
        for key in ("provider", "model"):
            if key in container:
                out.append(Signal("metadata:%s" % key, str(container[key])[:120],
                                  "响应 metadata 泄露 %s（wrapper 回传上游）" % key, "高"))
    return out


def parse_client_config(text):
    """§2.3 客户端工件：从 JS 文本抽 apiBase/assistantEndpoint/featureFlags。"""
    raw = text or ""
    out = []
    for key in CLIENT_CONFIG_KEYS:
        for match in re.finditer(r'["\']?%s["\']?\s*[:=]\s*([^,;}\n]+)' % re.escape(key), raw):
            value = match.group(1).strip().strip("\"'")[:120]
            if value:
                out.append(Signal("client:%s" % key, value,
                                  "前端工件配置键 %s（§2.3 JS 配置泄露）" % key, "中"))
            break
    return out


def probe_threshold_series(stages):
    """§2.3 检索阈值递减：exact→synonym→misspelling，观察检索由触发转不触发。

    每 stage 为 {stage, triggered(bool), score?}；至少两级且存在状态翻转才下结论，
    否则不可判定（避免单样本推断阈值）。
    """
    items = [s for s in (stages or []) if isinstance(s, dict) and
             s.get("stage") in THRESHOLD_STAGES]
    if len(items) < 2:
        return Finding("检索阈值递减", Existence.UNDETERMINED.value, [],
                       "递减样本 <2，无法观察翻转")
    flags = [bool(s.get("triggered")) for s in items]
    signals = [Signal("threshold:%s" % s["stage"],
                      "触发" if s.get("triggered") else "未触发",
                      "递减探测阶段 %s（score=%s）" % (s["stage"], s.get("score", "n/a")), "中")
               for s in items]
    flipped = any(a != b for a, b in zip(flags, flags[1:]))
    note = "出现检索触发翻转，提示阈值边界" if flipped else "各阶段检索状态一致，未见阈值边界"
    return Finding("检索阈值递减",
                   Existence.PRESENT.value if flipped else Existence.UNDETERMINED.value,
                   signals, note)


def assess_log_visibility(log):
    """§2.4 防御视角：日志捕获字段与检测覆盖缺口（无语义/意图/跨会话关联）。"""
    if not log:
        return Finding("交互日志可见性", Existence.UNDETERMINED.value, [], "无日志观测")
    data = log if isinstance(log, dict) else {}
    captured = [str(f) for f in LOG_FIELDS if f in data]
    present_gaps = [g for g in LOG_GAPS if g in data]
    signals = []
    if captured:
        signals.append(Signal("log:fields", "、".join(captured),
                              "防御日志捕获字段（§2.4 原始取证）", "中"))
    for gap in present_gaps:
        signals.append(Signal("log:gap", gap,
                              "检测覆盖缺口：%s（SIEM 原始日志无语义分析）" % gap, "高"))
    # 未显式声明的缺口不作为「已观测事实」，只在实际给出日志能力清单时评估。
    note = "命中捕获字段 %d 项，显式缺口 %d 项" % (len(captured), len(present_gaps))
    return Finding("交互日志可见性",
                   Existence.PRESENT.value if captured or present_gaps else Existence.UNDETERMINED.value,
                   signals, note)


def analyze(observations):
    """汇总入口：消费观测 dict，产出结构化分析（不发起任何请求）。"""
    obs = observations if isinstance(observations, dict) else {}
    items = obs.get("observations") or []
    header_signals, health_signals = [], []
    metadata_signals = []
    behavior_obs, source_groups = [], []
    canary_findings, detection_hits, paths = [], [], []
    repo_files = {}
    statuses = []
    extra_findings = []
    for item in items:
        if not isinstance(item, dict):
            continue
        kind = str(item.get("kind") or "")
        if kind == "headers":
            header_signals.extend(parse_ai_headers(item.get("headers")))
        elif kind == "health":
            health_signals.extend(parse_health_config(item.get("body")))
        elif kind == "endpoint":
            statuses.append({"url": item.get("url", ""),
                             "verdict": classify_endpoint_status(item.get("status"))})
        elif kind == "chat":
            behavior_obs.append(item)
        elif kind == "rag":
            source_groups.extend(parse_rag_sources(item.get("body")))
        elif kind == "canary":
            canary_findings.append(detect_canary(item.get("text")))
        elif kind == "detection":
            detection_hits.extend(assess_detection(item.get("query")))
        elif kind == "sequence":
            burst = endpoint_burst_risk(item.get("paths"))
            if burst:
                detection_hits.append(burst)
        elif kind == "repository":
            repo_files.update(item.get("files") or {})
        elif kind == "self_describe":
            extra_findings.append(parse_self_describing(item.get("schema")))
        elif kind == "metadata":
            metadata_signals.extend(parse_response_metadata(item.get("body")))
        elif kind == "client_config":
            cfg_signals = parse_client_config(item.get("text"))
            extra_findings.append(Finding(
                "客户端配置泄露",
                Existence.PRESENT.value if cfg_signals else Existence.UNDETERMINED.value,
                cfg_signals, "JS 工件配置键（§2.3）"))
        elif kind == "threshold":
            extra_findings.append(probe_threshold_series(item.get("stages")))
        elif kind == "log_view":
            extra_findings.append(assess_log_visibility(item.get("log")))
        elif kind == "shadow":
            extra_findings.append(parse_shadow_endpoints(item))
    findings = [
        fingerprint_behavior(behavior_obs),
        map_knowledge_base(source_groups),
    ] + canary_findings + extra_findings
    if detection_hits:
        findings.append(Finding("检测规则命中", "命中", detection_hits,
                                "关键词/时序匹配，不代表语义意图"))
    return {
        "target": obs.get("target", ""),
        "profile": obs.get("profile", "passive"),
        "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "taxonomy": [{"layer": layer, "steps": list(steps), "properties": props}
                     for layer, steps, props in TAXONOMY],
        "signals": [s.to_dict() for s in header_signals + health_signals + metadata_signals],
        "endpoints": statuses,
        "findings": [f.to_dict() for f in findings],
        "disclosure": [classify_disclosure(
            {s.kind.split(":", 1)[1]: s.value for s in g}) for g in source_groups],
        "repository": mine_repository(repo_files),
        "covert": covert_rewrite(str(obs.get("query", "")), detection_hits),
        "pacing": pacing_plan(obs.get("profile", "passive")),
    }


def validate_analysis(result):
    """校验：结论须有依据；单信号不得定家族；401/404 不得错判；凭据不落明文。"""
    violations = []
    for finding in (result or {}).get("findings", []):
        positive = finding.get("verdict") in (Existence.PRESENT.value, "命中")
        if not finding.get("signals") and positive:
            violations.append("%s 无信号却给出肯定结论" % finding.get("name"))
        for signal in finding.get("signals", []):
            if not signal.get("basis"):
                violations.append("%s/%s 缺判定依据" % (finding.get("name"),
                                                      signal.get("kind")))
            if signal.get("kind") == "canary:password" and \
                    not str(signal.get("value", "")).startswith("Bearer-"):
                violations.append("诱饵凭据未脱敏：%s" % signal.get("kind"))
            if signal.get("kind", "").startswith("metadata:") and \
                    re.search(r"(sk-|api[_-]?key\s*[:=]|AKIA[0-9A-Z]{16})",
                              str(signal.get("value", "")), re.I):
                violations.append("metadata 字段疑似明文凭据：%s" % signal.get("kind"))
        if finding.get("name") == "模型行为指纹" and finding.get("family") and \
                finding.get("verdict") != Existence.PRESENT.value:
            violations.append("模型家族结论缺存在性基底")
    for endpoint in (result or {}).get("endpoints", []):
        if endpoint.get("verdict") not in ("PRESENT", "AUTH_REQUIRED",
                                           "ABSENT", "UNDETERMINED"):
            violations.append("端点状态非法：%s" % endpoint.get("verdict"))
    return violations
