#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""声明式探测规格：7 步 = 请求规格 + 解析器 + 判据（recon-01..recon-07）。

设计要点
  - 每条 step 只声明「发什么、怎么解析、凭什么判定」，不含调度逻辑；
  - 判据返回存在性三值（model.Existence），禁止布尔；
  - 对抗性探针不在此模块，`recon-07` 默认仅做无害回显观察。
"""
import json
import re
from dataclasses import dataclass, field
from typing import Callable, Dict, Optional, Tuple

from .model import Category, Existence
from . import fingerprint

ECHO_MARKER = "RECON-PROBE-OK"
SECURITY_HEADERS = ("Content-Security-Policy", "X-Frame-Options",
                    "X-Content-Type-Options", "Strict-Transport-Security",
                    "Referrer-Policy", "Permissions-Policy")
SPA_SIGNATURE = re.compile(r"<!doctype html", re.I)
BUNDLE_RE = re.compile(r'src="(/assets/[^"]+\.js)"')


# --------------------------------------------------------------------------
# 请求 / 步骤规格
# --------------------------------------------------------------------------
@dataclass(frozen=True)
class RequestSpec:
    """一次请求的声明。`path_fn` 用于依赖前序响应的动态路径（如前端 bundle 名）。"""

    label: str
    method: str
    path: str = ""
    json_body: Optional[dict] = None
    timeout: int = 30
    path_fn: Optional[Callable[[dict], str]] = None
    collect: Optional[Callable[[object], dict]] = None
    tag: str = ""    # 请求标签（如 port-probe），供判据区分主动端口探测


@dataclass(frozen=True)
class StepSpec:
    """一个 recon 步骤：类别 + 被动请求 + 主动请求 + 判据。"""

    step_id: str
    title: str
    category: Category
    purpose: str
    judge: str
    requests: Tuple[RequestSpec, ...] = ()
    active_requests: Tuple[RequestSpec, ...] = ()
    reuse: str = ""


@dataclass
class Judgement:
    """判据输出：存在性 + 签名 + 注记 + 回写上下文。"""

    existence: Existence
    product: str = ""
    version: str = ""
    signature: str = ""
    note: str = ""
    context: dict = field(default_factory=dict)


# --------------------------------------------------------------------------
# 解析工具
# --------------------------------------------------------------------------
@dataclass
class SseView:
    events: Tuple[str, ...] = ()
    text: str = ""
    meta: dict = field(default_factory=dict)
    mcp_results: int = 0


def parse_sse(body):
    """解析 Server-Sent Events：事件类型集合、拼接文本、meta 字段、MCP 结果数。"""
    events, chunks, meta, mcp = [], [], {}, 0
    for block in (body or "").split("\n\n"):
        event, data_lines = "", []
        for line in block.splitlines():
            if line.startswith("event:"):
                event = line.split(":", 1)[1].strip()
            elif line.startswith("data:"):
                data_lines.append(line.split(":", 1)[1].lstrip())
        if not data_lines:
            continue
        events.append(event or "message")
        payload = "\n".join(data_lines)
        try:
            obj = json.loads(payload)
        except (ValueError, TypeError):
            chunks.append(payload)
            continue
        if not isinstance(obj, dict):
            continue
        if "content" in obj:
            chunks.append(str(obj.get("content", "")))
        elif "mcpResult" in obj or "mcp_result" in obj:
            mcp += 1
            chunks.append("MCP_RESULT: " + json.dumps(obj, ensure_ascii=False)[:400])
        elif "lab_id" in obj or "request_id" in obj:
            meta.update(obj)
    return SseView(tuple(dict.fromkeys(events)), "".join(chunks), meta, mcp)


def is_spa_fallback(result):
    """SPA 回退判据：200 + text/html + doctype（任何未知路径都如此）。"""
    return (result.status == 200
            and "html" in (result.content_type or "").lower()
            and bool(SPA_SIGNATURE.search(result.body or "")))


def missing_security_headers(headers):
    """返回缺失的安全响应头名（护栏面客观依据）。"""
    lowered = {k.lower() for k in (headers or {})}
    return [h for h in SECURITY_HEADERS if h.lower() not in lowered]


def curl_command(method, url, json_body=None):
    """生成可直接 copy/paste 的复现命令（§6.1 可复现性）。"""
    if method.upper() == "GET":
        return "curl -s %s" % url
    body = json.dumps(json_body or {}, ensure_ascii=False)
    return ("curl -s -N -X %s %s -H 'Content-Type: application/json' -d '%s'"
            % (method.upper(), url, body))


# --------------------------------------------------------------------------
# 判据（recon-01..07）
# --------------------------------------------------------------------------
def judge_engine(results, ctx):
    """recon-01：从运行时响应命名模型；模型清单端点缺失时记「不存在」。"""
    conf = results[0] if results else None
    catalog = results[1] if len(results) > 1 else None
    if conf is None or conf.error:
        return Judgement(Existence.UNDETERMINED, note="部署配置不可达：%s"
                         % (conf.error if conf else "无响应"))
    hit = fingerprint.primary(conf, Category.LLM_ENGINE)
    notes = []
    if hit:
        notes.append("部署配置暴露默认模型 `%s`" % hit.product)
        if catalog is not None:
            if getattr(catalog, "existence", None) == Existence.ABSENT:
                notes.append("模型清单端点（/v1/models）判定不存在（SPA 回退页），"
                             "不据此新增资产")
            elif catalog.ok:
                notes.append("模型清单端点可用（HTTP %d）" % catalog.status)
        return Judgement(
            Existence.PRESENT, product=hit.product or "不可判定",
            version=hit.version or "不可判定", signature=hit.signature,
            note="；".join(notes), context={"model": hit.product})
    return Judgement(Existence.UNDETERMINED,
                     note="未见 LLM 引擎运行时指纹（被动面）")


def judge_model_service(results, ctx):
    """recon-02：枚举模型服务端点、会话面与流式结构。"""
    chat = results[0] if results else None
    runs = results[1] if len(results) > 1 else None
    if chat is None or chat.error:
        return Judgement(Existence.UNDETERMINED,
                         note="聊天端点不可达：%s" % (chat.error if chat else "无响应"))
    sse = parse_sse(chat.body)
    notes = []
    if sse.events:
        notes.append("SSE 事件类型：%s" % "、".join(sse.events))
    if sse.meta.get("request_id"):
        notes.append("request_id 可见（%s…）" % str(sse.meta["request_id"])[:8])
    for key in ("lab_id", "phase", "control_mode", "artifact_replay"):
        if key in sse.meta:
            notes.append("%s=%s" % (key, sse.meta[key]))
    if runs is not None and not runs.error:
        notes.append("运行遥测端点 HTTP %d（%s）"
                     % (runs.status, "可匿名读取" if runs.ok else "受限"))
    existence = Existence.PRESENT if sse.events else Existence.UNDETERMINED
    product = "SSE 流式聊天面" if sse.events else "不可判定"
    return Judgement(existence, product=product, version="不可判定",
                     signature="event: %s" % (sse.events[0] if sse.events else ""),
                     note="；".join(notes),
                     context={"sse": sse, "chat": chat, "runs": runs,
                              "phase": str(sse.meta.get("phase", "") or "")})


def judge_rag(results, ctx):
    """recon-03：以检索链路痕迹判定 RAG 存在与框架族。"""
    bundle = results[-1] if results else None
    if bundle is None or bundle.error:
        return Judgement(Existence.UNDETERMINED, note="前端产物不可达，无法取检索痕迹")
    hit = fingerprint.primary(bundle, Category.RAG)
    if hit:
        return Judgement(Existence.PRESENT, product=hit.product,
                         version="不可判定", signature=hit.signature,
                         note="前端产物含检索链路痕迹（%s）→ 存在 RAG 面；具体框架不可判定"
                         % hit.signature)
    return Judgement(Existence.UNDETERMINED, product="不可判定",
                     note="未检出检索链路痕迹")


def _port_list():
    """从 recon-04 的主动请求声明生成本步端口清单（避免二处硬编码，C1）。"""
    spec = find("recon-04")
    return "/".join(r.label.split(":")[-1] for r in spec.active_requests)


def judge_vector(results, ctx):
    """recon-04：向量库发现。passive 面无端口证据 → 不可判定（AC-09）。"""
    profile = ctx.get("profile", "passive")
    ports = [r for r in results if r.note == "port-probe"]
    if profile != "active" or not ports:
        return Judgement(Existence.UNDETERMINED, product="不可判定",
                         note="被动面无独立向量库端口证据；「未发现」不等于「不存在」，"
                              "需 --profile active 定向探测（%s）" % _port_list())
    alive = [r for r in ports if r.ok and not is_spa_fallback(r)]
    if alive:
        return Judgement(Existence.PRESENT, product="向量库（端口存活，实现不可判定）",
                         version="不可判定",
                         signature="、".join(r.url for r in alive),
                         note="主动探测发现存活端口：%s" % "、".join(r.url for r in alive))
    return Judgement(Existence.ABSENT, product="无", version="无",
                     note="主动探测：定向端口全部关闭（%s）"
                          % "、".join(r.url for r in ports))


def judge_agent(results, ctx):
    """recon-05：识别编排 / 多智能体痕迹。"""
    schema = results[0] if results else None
    runs = results[1] if len(results) > 1 else None
    if schema is None or schema.error:
        return Judgement(Existence.UNDETERMINED, note="编排面不可达")
    has_param = "request_id" in (schema.body or "")
    notes = []
    if has_param:
        notes.append("实验面接口暴露 `request_id` 语义（HTTP %d）" % schema.status)
    if runs is not None and not runs.error:
        notes.append("运行遥测端点 HTTP %d" % runs.status)
    if not notes:
        return Judgement(Existence.UNDETERMINED, note="未见编排/智能体痕迹")
    notes.append("依据为编排面 schema + 遥测端点；具体 agent 框架不可判定（推断）")
    return Judgement(Existence.PRESENT, product="agent 编排面（推断，框架不可判定）",
                     version="不可判定", signature="request_id schema",
                     note="；".join(notes))


def judge_mcp(results, ctx):
    """recon-06：工具面与凭据校验预言机（含 200+success:false 语义）。"""
    oracle = results[0] if results else None
    if oracle is None or oracle.error:
        return Judgement(Existence.UNDETERMINED, note="MCP 校验端点不可达")
    body = oracle.body or ""
    explicit = re.search(r'"success"\s*:\s*(true|false)', body)
    notes = []
    if explicit:
        notes.append("失败语义为 HTTP %d + `success:%s`（禁以状态码判失败）"
                     % (oracle.status, explicit.group(1)))
    if oracle.status == 422:
        notes.append("参数校验 422 暴露字段名，可枚举工具面契约")
    if not explicit and oracle.status != 422:
        return Judgement(Existence.UNDETERMINED, note="未见 MCP 工具面痕迹")
    notes.append("身份边界：匿名可调用校验接口")
    return Judgement(Existence.PRESENT, product="凭据校验预言机（MCP 信任边界面）",
                     version="不可判定", signature=explicit.group(0) if explicit else "422 schema",
                     note="；".join(notes))


def judge_guardrail(results, ctx):
    """recon-07：护栏行为与安全响应头（复用 recon-02 的聊天响应，不重复请求）。"""
    chat = ctx.get("reuse_chat")
    headers = ctx.get("headers") or {}
    if chat is None or chat.error:
        return Judgement(Existence.UNDETERMINED, note="无聊天响应可判读")
    sse = parse_sse(chat.body)
    notes, behavior = [], ""
    if ECHO_MARKER in sse.text:
        behavior = "护栏放行原样回显"
        notes.append("无害回显探针被原样返回（%s）" % ECHO_MARKER)
    elif re.search(r"(can't|cannot|unable|抱歉|无法|拒绝)", sse.text, re.I):
        behavior = "护栏拒答"
        notes.append("无害回显探针被拒答")
    else:
        behavior = "护栏改写/截断"
        notes.append("响应未原样回显，疑经改写或截断")
    missing = missing_security_headers(headers)
    if missing:
        notes.append("缺失安全响应头：%s" % "、".join(missing))
    else:
        notes.append("安全响应头齐全")
    notes.append("control_mode=%s" % (sse.meta.get("control_mode") or "未知"))
    return Judgement(Existence.PRESENT, product="护栏（%s）" % behavior,
                     version="不可判定", signature=behavior,
                     note="；".join(notes), context={"behavior": behavior,
                                                     "missing_headers": missing})


JUDGES: Dict[str, Callable] = {
    "engine": judge_engine,
    "model_service": judge_model_service,
    "rag": judge_rag,
    "vector": judge_vector,
    "agent": judge_agent,
    "mcp": judge_mcp,
    "guardrail": judge_guardrail,
}


# --------------------------------------------------------------------------
# 步骤表（7 步，与 SKILL.md 一一对应）
# --------------------------------------------------------------------------
def _collect_bundle(resp):
    m = BUNDLE_RE.search(resp.body or "")
    return {"bundle": m.group(1)} if m else {}


def _port(port, label):
    return RequestSpec(label="%s:%d" % (label, port), method="GET",
                       path="http://{host}:%d/" % port, timeout=3,
                       tag="port-probe")


STEP_SPECS: Tuple[StepSpec, ...] = (
    StepSpec(
        step_id="recon-01", title="LLM 引擎识别", category=Category.LLM_ENGINE,
        purpose="从运行时响应命名模型与引擎族；模型清单端点缺失时记「不存在」",
        judge="engine",
        requests=(
            RequestSpec("部署配置", "GET", "/api/config", timeout=10),
            RequestSpec("模型清单（可选）", "GET", "/v1/models", timeout=10),
        ),
    ),
    StepSpec(
        step_id="recon-02", title="模型服务枚举", category=Category.MODEL_SERVICE,
        purpose="枚举模型服务端点、会话面与流式结构（单次无害回显）",
        judge="model_service",
        requests=(
            RequestSpec("聊天端点（无害回显）", "POST", "/api/labs/{lab}/chat",
                        json_body={"prompt": "Reply with exactly: " + ECHO_MARKER},
                        timeout=120),
            RequestSpec("运行遥测", "GET", "/api/me/runs?limit=1", timeout=10),
        ),
    ),
    StepSpec(
        step_id="recon-03", title="RAG 库探测", category=Category.RAG,
        purpose="以检索链路痕迹判定 RAG 存在与框架族",
        judge="rag",
        requests=(
            RequestSpec("入口页", "GET", "/explore", timeout=15, collect=_collect_bundle),
            RequestSpec("前端产物", "GET", "", timeout=20,
                        path_fn=lambda ctx: ctx.get("bundle") or "/assets/index.js"),
        ),
    ),
    StepSpec(
        step_id="recon-04", title="向量库发现", category=Category.VECTOR_DB,
        purpose="发现向量数据库端口与健康检查；无证据时记「不可判定」",
        judge="vector",
        requests=(
            RequestSpec("向量库实验面", "GET", "/api/labs/MM_05/summary", timeout=10),
        ),
        active_requests=(
            _port(6333, "qdrant"), _port(8080, "weaviate"),
            _port(19530, "milvus"), _port(8000, "chroma"),
        ),
    ),
    StepSpec(
        step_id="recon-05", title="agent 系统识别", category=Category.AGENT,
        purpose="识别编排/多智能体痕迹与遥测面",
        judge="agent",
        requests=(
            RequestSpec("agentic 实验面", "GET", "/api/labs/DE_01/summary", timeout=10),
            RequestSpec("运行遥测", "GET", "/api/me/runs?limit=1", timeout=10),
        ),
    ),
    StepSpec(
        step_id="recon-06", title="MCP·工具面发现", category=Category.MCP,
        purpose="枚举工具面与凭据校验预言机，记录失败语义",
        judge="mcp",
        requests=(
            RequestSpec("凭据校验（错误答案，单次）", "POST", "/api/secrets/validate",
                        json_body={"labId": "MCP_01", "answer": "recon-probe"},
                        timeout=10),
            RequestSpec("MCP 实验面", "GET", "/api/labs/MCP_01/summary", timeout=10),
        ),
    ),
    StepSpec(
        step_id="recon-07", title="护栏与输入输出探测", category=Category.GUARDRAIL,
        purpose="无害回显观察护栏行为 + 安全响应头（复用 recon-02 响应，不重复请求）",
        judge="guardrail", reuse="recon-02",
    ),
)


def find(step_id):
    for spec in STEP_SPECS:
        if spec.step_id == step_id:
            return spec
    raise KeyError("未知步骤：%s" % step_id)


def step_requests(spec, profile):
    """返回该步骤在当前分级下实际要发的请求（被动 + 可选主动）。"""
    reqs = list(spec.requests)
    if profile == "active":
        reqs += list(spec.active_requests)
    return reqs
