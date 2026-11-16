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
    basis: str = ""      # 判定依据（可复核的一句话，C6）
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
    """recon-01：从运行时响应命名模型；模型清单缺失时记「不存在」。"""
    conf = results[0] if results else None
    catalog = results[1] if len(results) > 1 else None
    if conf is None or conf.error:
        return Judgement(Existence.UNDETERMINED,
                         note="部署配置不可达：%s"
                              % (conf.error if conf else "无响应"),
                         basis="部署配置请求未获得响应")
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
            note="；".join(notes), basis="部署配置响应含 `llm_model_default` 字段",
            context={"model": hit.product})
    plan = ctx.get("plan")
    if plan is not None and getattr(plan, "family", "unknown") != "unknown":
        basis = ("应用族=%s，基路径=`%s`；运行时配置端点未暴露模型名"
                 % (plan.family, plan.base_path or "/"))
        note = "未见 LLM 引擎运行时指纹（发现阶段识别为 %s）" % plan.family
    else:
        basis = "部署配置与模型清单均未命中 LLM 引擎运行时指纹"
        note = "未见 LLM 引擎运行时指纹（被动面）"
    return Judgement(Existence.UNDETERMINED, note=note, basis=basis)


def _model_catalog(results):
    """从已试端点中找模型清单（OpenAI 兼容 / Ollama），返回 (结果, 产品, 依据)。"""
    for result in results:
        if result is None or result.error or not result.ok or is_spa_fallback(result):
            continue
        path = result.url.split("?")[0].rstrip("/")
        body = result.body or ""
        if path.endswith("/v1/models") and '"data"' in body:
            return result, "OpenAI 兼容模型服务（/v1/models）", "模型清单含 data 数组"
        if path.endswith("/api/tags") and '"models"' in body:
            return result, "Ollama 模型服务（/api/tags）", "模型清单含 models 数组"
    return None, "", ""


def judge_model_service(results, ctx):
    """recon-02：枚举模型服务端点、会话面与流式结构。"""
    chat = results[0] if results else None
    runs = results[1] if len(results) > 1 else None
    if chat is None or chat.error:
        return Judgement(Existence.UNDETERMINED,
                         note="聊天端点不可达：%s" % (chat.error if chat else "无响应"),
                         basis="聊天端点请求未获得响应")
    sse = parse_sse(chat.body)
    if not sse.events:
        catalog, product, why = _model_catalog(results)
        if catalog is not None:
            return Judgement(Existence.PRESENT, product=product,
                             version="不可判定", signature=catalog.url,
                             note="%s（HTTP %d）" % (why, catalog.status),
                             basis="%s 返回 %s" % (catalog.url, why))
        basis = ("聊天端点返回 SPA 回退页（非 SSE）" if is_spa_fallback(chat)
                 else "聊天响应未含 SSE 事件")
        return Judgement(Existence.UNDETERMINED, product="不可判定",
                         note="未发现模型服务端点：%s（HTTP %d）"
                              % (basis, chat.status), basis=basis)
    notes = []
    if sse.meta.get("request_id"):
        notes.append("request_id 可见（%s…）" % str(sse.meta["request_id"])[:8])
    for key in ("lab_id", "phase", "control_mode", "artifact_replay"):
        if key in sse.meta:
            notes.append("%s=%s" % (key, sse.meta[key]))
    if runs is not None and not runs.error:
        notes.append("运行遥测端点 HTTP %d（%s）"
                     % (runs.status, "可匿名读取" if runs.ok else "受限"))
    notes.insert(0, "SSE 事件类型：%s" % "、".join(sse.events))
    return Judgement(Existence.PRESENT, product="SSE 流式聊天面",
                     version="不可判定", signature="event: %s" % sse.events[0],
                     note="；".join(notes),
                     basis="聊天端点返回 SSE 事件（%s）" % "、".join(sse.events),
                     context={"sse": sse, "chat": chat, "runs": runs,
                              "phase": str(sse.meta.get("phase", "") or "")})


def judge_rag(results, ctx):
    """recon-03：以检索链路痕迹判定 RAG 存在与框架族（扫描全部已试端点）。"""
    if not results:
        return Judgement(Existence.UNDETERMINED, note="无前端产物可判读",
                         basis="未执行前端产物请求")
    tried = 0
    for result in results:
        if result is None or result.error:
            continue
        tried += 1
        hit = fingerprint.primary(result, Category.RAG)
        if hit:
            return Judgement(Existence.PRESENT, product=hit.product,
                             version="不可判定", signature=hit.signature,
                             note="前端产物含检索链路痕迹（%s）→ 存在 RAG 面；"
                                  "具体框架不可判定" % hit.signature,
                             basis="%s 命中检索痕迹" % result.url)
    return Judgement(Existence.UNDETERMINED, product="不可判定",
                     note="未检出检索链路痕迹（已试 %d 个端点）" % tried,
                     basis="已试 %d 个端点均无检索链路痕迹" % tried)



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
                              "需 --profile active 定向探测（%s）" % _port_list(),
                         basis="被动档未执行向量库端口探测")
    alive = [r for r in ports if r.ok and not is_spa_fallback(r)]
    if alive:
        return Judgement(Existence.PRESENT, product="向量库（端口存活，实现不可判定）",
                         version="不可判定",
                         signature="、".join(r.url for r in alive),
                         note="主动探测发现存活端口：%s" % "、".join(r.url for r in alive),
                         basis="定向端口存活：%s" % "、".join(r.url for r in alive))
    return Judgement(Existence.ABSENT, product="无", version="无",
                     note="主动探测：定向端口全部关闭（%s）"
                          % "、".join(r.url for r in ports),
                     basis="主动探测 %d 个定向端口全部不可达" % len(ports))


def judge_agent(results, ctx):
    """recon-05：识别编排 / 多智能体痕迹。"""
    schema = results[0] if results else None
    runs = results[1] if len(results) > 1 else None
    if schema is None or schema.error:
        return Judgement(Existence.UNDETERMINED, note="编排面不可达",
                         basis="编排面请求未获得响应")
    if is_spa_fallback(schema):
        return Judgement(Existence.UNDETERMINED, product="不可判定",
                         note="编排面返回 SPA 回退页（HTTP %d），无 schema 证据"
                              % schema.status,
                         basis="编排面响应为 SPA 回退页，不构成编排证据")
    has_param = "request_id" in (schema.body or "")
    notes = []
    if has_param:
        notes.append("实验面接口暴露 `request_id` 语义（HTTP %d）" % schema.status)
    runs_ok = (runs is not None and not runs.error and runs.ok
               and not is_spa_fallback(runs))
    if runs_ok:
        notes.append("运行遥测端点 HTTP %d" % runs.status)
    if not has_param and not runs_ok:
        return Judgement(Existence.UNDETERMINED, note="未见编排/智能体痕迹",
                         basis="编排面 schema 与遥测端点均无编排痕迹")
    notes.append("依据为编排面 schema + 遥测端点；具体 agent 框架不可判定（推断）")
    return Judgement(Existence.PRESENT, product="agent 编排面（推断，框架不可判定）",
                     version="不可判定", signature="request_id schema",
                     note="；".join(notes),
                     basis="实验面 schema 暴露 `request_id` 或遥测端点可读")


def _openapi_surface(results):
    """扫描已试端点中的 OpenAPI 描述（工具面的客观证据）。"""
    for result in results:
        if result is None or result.error or not result.ok or is_spa_fallback(result):
            continue
        if not result.url.split("?")[0].rstrip("/").endswith("/openapi.json"):
            continue
        body = result.body or ""
        if '"openapi"' in body and ('"paths"' in body or '"tools"' in body):
            return result
    return None


def judge_mcp(results, ctx):
    """recon-06：工具面与凭据校验预言机（含 200+success:false 语义）。"""
    oracle = results[0] if results else None
    body = (oracle.body or "") if oracle is not None else ""
    explicit = re.search(r'"success"\s*:\s*(true|false)', body)
    openapi = None
    if oracle is None or oracle.error or (not explicit and oracle.status != 422):
        openapi = _openapi_surface(results)
        if openapi is not None:
            return Judgement(Existence.PRESENT, product="OpenAPI 工具面",
                             version="不可判定", signature="openapi.json",
                             note="`/openapi.json` 可匿名读取（HTTP %d），暴露工具面契约"
                                  % openapi.status,
                             basis="%s 返回 OpenAPI 描述" % openapi.url)
    if oracle is None or oracle.error:
        return Judgement(Existence.UNDETERMINED, note="MCP 校验端点不可达",
                         basis="MCP 校验端点请求未获得响应")
    notes = []
    if explicit:
        notes.append("失败语义为 HTTP %d + `success:%s`（禁以状态码判失败）"
                     % (oracle.status, explicit.group(1)))
    if oracle.status == 422:
        notes.append("参数校验 422 暴露字段名，可枚举工具面契约")
    if not explicit and oracle.status != 422:
        return Judgement(Existence.UNDETERMINED, note="未见 MCP 工具面痕迹",
                         basis="校验端点无 success 语义且无 OpenAPI 工具面")
    notes.append("身份边界：匿名可调用校验接口")
    return Judgement(Existence.PRESENT, product="凭据校验预言机（MCP 信任边界面）",
                     version="不可判定", signature=explicit.group(0) if explicit else "422 schema",
                     note="；".join(notes),
                     basis=("校验端点返回 `%s`" % explicit.group(0)) if explicit
                     else "校验端点返回 422 schema")


def judge_guardrail(results, ctx):
    """recon-07：护栏行为与安全响应头（复用 recon-02 的聊天响应，不重复请求）。"""
    chat = ctx.get("reuse_chat")
    headers = ctx.get("headers") or {}
    if chat is None or chat.error:
        return Judgement(Existence.UNDETERMINED, note="无聊天响应可判读",
                         basis="未获得聊天端点响应")
    sse = parse_sse(chat.body)
    if not sse.events or is_spa_fallback(chat):
        missing = missing_security_headers(headers)
        note = "聊天端点未返回 SSE（HTTP %d），无法判读护栏行为" % chat.status
        if missing:
            note += "；缺失安全响应头：%s" % "、".join(missing)
        return Judgement(Existence.UNDETERMINED, product="不可判定",
                         note=note, basis="聊天响应非 SSE（SPA 回退页或无事件）")
    notes, behavior = [], ""
    if ECHO_MARKER in sse.text:
        behavior = "放行原样回显"
        notes.append("无害回显探针被原样返回（%s）" % ECHO_MARKER)
    elif re.search(r"(can't|cannot|unable|抱歉|无法|拒绝)", sse.text, re.I):
        behavior = "拒答"
        notes.append("无害回显探针被拒答")
    else:
        behavior = "改写/截断"
        notes.append("响应未原样回显，疑经改写或截断")
    missing = missing_security_headers(headers)
    if missing:
        notes.append("缺失安全响应头：%s" % "、".join(missing))
    else:
        notes.append("安全响应头齐全")
    notes.append("control_mode=%s" % (sse.meta.get("control_mode") or "未知"))
    return Judgement(Existence.PRESENT, product="护栏（%s）" % behavior,
                     version="不可判定", signature=behavior,
                     note="；".join(notes), basis="聊天响应 SSE 文本可判读",
                     context={"behavior": behavior,
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
