#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""自适应发现（S4）：入口 → 应用族/基路径/版本 → 追加类端点证据。

只做被动 GET，请求上限 `MAX_DISCOVERY_REQUESTS`，不改变 7 步判据语义；
发现结果并入 recon-03 的证据片段，判据按需扫描（不新增资产类别）。
"""
import json
import re
import time
from dataclasses import dataclass, field
from typing import Dict, List
from urllib.parse import urlsplit

from . import probes
from .model import Existence, ProbeResult

MAX_DISCOVERY_REQUESTS = 12
HREF_RE = re.compile(r'href=["\']([^"\']+)["\']', re.I)
SCRIPT_SRC_RE = re.compile(r'<script[^>]+src=["\']([^"\']+)["\']', re.I)
STREAMLIT_VERSION_RE = re.compile(
    r'version\s*:\s*[`"\']([0-9]+\.[0-9]+\.[0-9]+)[`"\']')
GENERIC_VERSION_RE = re.compile(r'"version"\s*:\s*"([0-9]+\.[0-9]+\.[0-9]+)"')


@dataclass
class DiscoveryPlan:
    """一次发现的结果：应用族、基路径、版本、依据与全部探测响应。"""

    family: str = "unknown"
    base_path: str = ""
    version: str = ""
    entry_url: str = ""
    basis: List[str] = field(default_factory=list)
    results: List[ProbeResult] = field(default_factory=list)
    step_results: Dict[str, List[ProbeResult]] = field(default_factory=dict)
    signals: List[str] = field(default_factory=list)
    agent_count: int = 0
    agent_ids: List[str] = field(default_factory=list)
    chat_agent_id: str = ""
    mcp_agent_count: int = 0
    mcp_agent_ids: List[str] = field(default_factory=list)
    llm_provider: str = ""
    llm_model: str = ""
    agent_api: str = ""

    def add_signal(self, name):
        if name and name not in self.signals:
            self.signals.append(name)

    def describe(self):
        if self.family == "unknown":
            return "应用族未识别（按通用端点枚举）"
        return "应用族 %s，基路径 `%s`%s" % (
            self.family, self.base_path or "/",
            ("，版本 %s" % self.version) if self.version else "")

    def tried(self):
        return [{"method": r.method, "url": r.url,
                 "status": r.status, "error": r.error} for r in self.results]

    def to_dict(self):
        return {"family": self.family, "base_path": self.base_path,
                "version": self.version, "entry_url": self.entry_url,
                "basis": list(self.basis), "tried": self.tried(),
                "signals": list(self.signals),
                "agent_count": self.agent_count,
                "agent_ids": list(self.agent_ids),
                "chat_agent_id": self.chat_agent_id,
                "mcp_agent_count": self.mcp_agent_count,
                "mcp_agent_ids": list(self.mcp_agent_ids),
                "llm_provider": self.llm_provider,
                "llm_model": self.llm_model,
                "agent_api": self.agent_api}


def _fetch(transport, url, timeout, plan, json_body=None, method="GET",
           step="recon-03"):
    """发一次发现请求并记录；任何异常都转为 error 结果，不中断发现。"""
    if len(plan.results) >= MAX_DISCOVERY_REQUESTS:
        return None
    result = ProbeResult(step_id=step, url=url, method=method,
                         command=probes.curl_command(method, url, json_body),
                         request_body=dict(json_body or {}), note="discovery")
    t0 = time.time()
    try:
        resp = transport.request(method, url, json_body, timeout=timeout)
    except Exception as exc:
        result.error = "传输异常：%s" % exc
        result.elapsed_ms = int((time.time() - t0) * 1000)
        _record(plan, result, step)
        return result
    result.status = resp.status
    result.body = resp.body or ""
    result.headers = resp.headers or {}
    result.content_type = resp.content_type or ""
    result.error = resp.error or ""
    result.elapsed_ms = resp.elapsed_ms or int((time.time() - t0) * 1000)
    if result.error:
        result.existence = Existence.UNDETERMINED
    elif probes.is_spa_fallback(result):
        result.existence = Existence.ABSENT
    elif result.ok:
        result.existence = Existence.PRESENT
    else:
        result.existence = Existence.UNDETERMINED
    _record(plan, result, step)
    return result


def _record(plan, result, step):
    plan.results.append(result)
    plan.step_results.setdefault(step, []).append(result)


def _json_body(result):
    if result is None or result.error or not result.ok:
        return None
    try:
        return json.loads(result.body or "")
    except (TypeError, ValueError):
        return None


def _candidate_bases(body):
    """从入口页链接提取浅层基路径候选（排除静态文件与深层路径）。"""
    out = []
    for href in HREF_RE.findall(body or "")[:80]:
        if not href.startswith("/") or href.startswith("//"):
            continue
        path = href.split("#")[0].split("?")[0].rstrip("/")
        if not path or path == "/" or path.count("/") > 2:
            continue
        # 末段含「.」即静态文件（favicon.ico、site.webmanifest、index-*.js 等），
        # 不依赖扩展名白名单：任意同类站点的静态资源都不得被当作应用基路径。
        if "." in path.rsplit("/", 1)[-1]:
            continue
        if path not in out:
            out.append(path)
    return out[:2]


def _join(target, base, suffix):
    return target + (base or "") + suffix


def _is_health_ok(result):
    return bool(result and result.ok and not probes.is_spa_fallback(result)
                and "html" not in (result.content_type or "").lower()
                and (result.body or "").strip().lower() in ("ok", ""))


def _resolve_script(target, base, src):
    if src.startswith("http://") or src.startswith("https://"):
        return src
    if src.startswith("/"):
        return target + src
    return _join(target, base, "/" + src.lstrip("./"))


def _version_from(body):
    for pattern in (STREAMLIT_VERSION_RE, GENERIC_VERSION_RE):
        match = pattern.search(body or "")
        if match:
            return match.group(1)
    return ""


def _origin(target):
    """把带路径的入口（如报告页 URL）归一化为 origin，避免拼出 `/x.html/` 死路。"""
    raw = target if "://" in target else "http://" + target
    parts = urlsplit(raw)
    if not parts.scheme or not parts.netloc:
        return target.rstrip("/")
    return "%s://%s" % (parts.scheme, parts.netloc)


def _agent_inventory(result):
    """把 /agents 的 JSON 数组识别为多智能体编排清单。"""
    data = _json_body(result)
    if not isinstance(data, list) or not data:
        return None
    if not all(isinstance(item, dict) for item in data):
        return None
    if not any("securityLevel" in item or "protocol" in item for item in data):
        return None
    return data


def _llm_status(result):
    data = _json_body(result)
    if not isinstance(data, dict):
        return ""
    model = str(data.get("model") or "").strip()
    provider = str(data.get("provider") or "").strip()
    if model and provider:
        return model
    return ""


def _mcp_agents(inventory):
    return [item for item in inventory
            if str(item.get("protocol") or "").lower() == "mcp"]


def _chat_entry_signals(body):
    """入口页的独立聊天入口标记（浮动按钮 / 直链 / iframe 嵌入）。"""
    marks = []
    if re.search(r'id=["\']aiFab["\']|ai-fab', body or "", re.I):
        marks.append("浮动按钮 #aiFab")
    if re.search(r'href=["\']/?chat/?["\']', body or "", re.I):
        marks.append("直链 /chat")
    if re.search(r'<iframe[^>]+src=["\']/?chat/?["\']', body or "", re.I):
        marks.append("iframe 嵌入 /chat")
    return marks


def discover(target, transport, timeout=15):
    """返回 `DiscoveryPlan`；请求数受上限约束，异常一律降级为「未识别」。"""
    requested = target.rstrip("/")
    target = _origin(target)
    plan = DiscoveryPlan()
    root = _fetch(transport, target + "/", timeout, plan)
    if root is None:
        return plan
    plan.entry_url = root.url
    if root.error:
        plan.basis.append("入口页不可达：%s" % root.error)
        return plan
    plan.basis.append("入口页 HTTP %d（%s）" % (root.status, root.content_type or "未知类型"))
    if requested != target:
        plan.basis.append("入口含路径，已按 origin 发现：`%s` → `%s`" % (requested, target))
        exact = _fetch(transport, requested, timeout, plan, step="recon-02")
        if exact is not None and not exact.error:
            marks = _chat_entry_signals(exact.body)
            if marks:
                plan.add_signal("chat_entry")
                plan.basis.append("报告页含独立聊天入口：%s（HTTP %d）"
                                  % ("、".join(marks), exact.status))
    marks = _chat_entry_signals(root.body)
    if marks and "chat_entry" not in plan.signals:
        plan.add_signal("chat_entry")
        plan.basis.append("入口页含独立聊天入口：%s" % "、".join(marks))
    if "AI Vulnerabilities Playground" in (root.body or "") or \
            "aivp-logo" in (root.body or ""):
        plan.family = "aivp"
        plan.add_signal("aivp_spa")
        plan.basis.append("入口页含 AIVP 品牌标记 → AIVP 演练平台")

    bases = [""] + _candidate_bases(root.body)
    for base in bases[:3]:
        health = _fetch(transport, _join(target, base, "/_stcore/health"),
                        timeout, plan)
        if _is_health_ok(health):
            plan.family = "streamlit"
            plan.base_path = base
            plan.add_signal("streamlit_health")
            # 成功的健康探针是 recon-02 的会话面证据；失败的尝试留在 recon-03
            plan.step_results.get("recon-03", []).remove(health)
            health.step_id = "recon-02"
            plan.step_results.setdefault("recon-02", []).append(health)
            plan.basis.append("健康端点 `%s` 返回 `ok` → Streamlit 运行时，基路径 `%s`"
                              % (health.url, base or "/"))
            break

    if plan.family == "streamlit":
        index = _fetch(transport, _join(target, plan.base_path, "/"), timeout, plan)
        if index is not None and not index.error:
            plan.entry_url = index.url
            plan.version = _version_from(index.body)
            if not plan.version:
                scripts = SCRIPT_SRC_RE.findall(index.body or "")
                for src in scripts[:4]:
                    if "static" not in src and "index" not in src and "main" not in src:
                        continue
                    bundle = _fetch(transport, _resolve_script(
                        target, plan.base_path, src), timeout, plan)
                    if bundle is not None:
                        plan.version = _version_from(bundle.body)
                    if plan.version:
                        break
        host_config = _fetch(transport, _join(
            target, plan.base_path, "/_stcore/host-config"), timeout, plan)
        if host_config is not None and host_config.ok:
            plan.add_signal("streamlit_host_config")
            plan.basis.append("`/_stcore/host-config` 可匿名读取（HTTP %d）"
                              % host_config.status)
        agent_doc = _fetch(transport, _join(
            target, plan.base_path, "/_stcore/agent/openapi.json"),
            timeout, plan, step="recon-06")
        if agent_doc is not None and agent_doc.ok:
            match = re.search(r'"x-streamlit-agent-api"\s*:\s*"(\w+)"',
                              agent_doc.body or "")
            if match:
                plan.agent_api = match.group(1)
                plan.add_signal("streamlit_agent_api")
                plan.basis.append("agent API 文档可读（HTTP %d，状态 `%s`）"
                                  % (agent_doc.status, plan.agent_api))
        if plan.version:
            plan.basis.append("前端产物标识版本 `%s`" % plan.version)
        return plan

    # 运行时 API 面：优先健康、agent 清单与模型状态，命中即收敛应用族
    health = _fetch(transport, target + "/health", timeout, plan, step="recon-05")
    if health is not None and health.ok and not probes.is_spa_fallback(health):
        try:
            data = json.loads(health.body or "")
        except (TypeError, ValueError):
            data = None
        if isinstance(data, dict) and str(data.get("status", "")).lower() == "ok":
            plan.add_signal("health")
            plan.basis.append("`/health` 返回运行时状态（HTTP %d）" % health.status)
            count = data.get("agents")
            if isinstance(count, int) and count > 0:
                plan.agent_count = count

    agents = _fetch(transport, target + "/agents", timeout, plan, step="recon-05")
    inventory = _agent_inventory(agents)
    if inventory is not None:
        plan.family = "dvaa"
        plan.agent_count = len(inventory)
        plan.agent_ids = [str(item.get("id") or "") for item in inventory
                          if item.get("id")]
        mcp_agents = _mcp_agents(inventory)
        plan.mcp_agent_count = len(mcp_agents)
        plan.mcp_agent_ids = [str(item.get("id") or "") for item in mcp_agents
                              if item.get("id")]
        api_agents = [item for item in inventory
                      if str(item.get("protocol") or "").lower() == "api"]
        # 只读回显优先选择低门槛 api agent（weak/critical/vulnerable），
        # 避免对 hardened agent 反复试探；选择仅依据清单声明字段。
        weak = [item for item in api_agents
                if str(item.get("securityLevel") or "").lower()
                in ("weak", "critical", "vulnerable")]
        preferred = [item for item in weak if "helper" in str(item.get("id") or "")]
        chosen = (preferred or weak or api_agents)
        if chosen:
            plan.chat_agent_id = str(chosen[0].get("id") or "")
            plan.basis.append("聊天面选定低门槛 agent `%s`（依据清单 securityLevel）"
                              % plan.chat_agent_id)
        plan.add_signal("agent_inventory")
        if plan.mcp_agent_count:
            plan.add_signal("mcp_agents_declared")
        plan.basis.append("`/agents` 暴露 %d 个 agent（MCP %d 个）→ DVAA 式编排面"
                          % (plan.agent_count, plan.mcp_agent_count))

    status = _fetch(transport, target + "/api/llm/status", timeout, plan,
                    step="recon-01")
    plan.llm_model = _llm_status(status)
    if plan.llm_model:
        plan.add_signal("llm_status")
        plan.llm_provider = str((_json_body(status) or {}).get("provider") or "")
        plan.basis.append("`/api/llm/status` 暴露模型 `%s`（%s）"
                          % (plan.llm_model, plan.llm_provider or "provider 未知"))

    if plan.family == "dvaa":
        host = urlsplit(target).hostname or ""
        ports = [int(item.get("port")) for item in _mcp_agents(inventory or [])
                 if str(item.get("port") or "").isdigit()][:4]
        for port in ports:
            if host:
                _fetch(transport, "http://%s:%d/mcp/tools" % (host, port),
                       min(timeout, 6), plan, step="recon-06")
        return plan

    # 通用类端点：仅在已知基路径（或根）各探一次，命中即更新应用族
    probe_base = plan.base_path if plan.family != "unknown" else ""
    checks = (
        ("/config", "gradio", "Gradio 配置"),
        ("/openapi.json", "openapi", "OpenAPI 描述"),
    )
    for suffix, family, label in checks:
        result = _fetch(transport, _join(target, probe_base, suffix), timeout, plan)
        if result is not None and result.ok and not probes.is_spa_fallback(result):
            if family == "gradio" and '"components"' in (result.body or ""):
                plan.family = plan.family if plan.family not in ("unknown",) else "gradio"
                plan.basis.append("`%s` 返回组件配置 → Gradio" % result.url)
            elif family == "openapi" and '"openapi"' in (result.body or ""):
                plan.family = plan.family if plan.family not in ("unknown",) else "openapi"
                plan.basis.append("`%s` 返回 OpenAPI 描述" % result.url)

    for suffix, family, label, marker in (
        ("/v1/models", "openai", "OpenAI 兼容模型清单", '"data"'),
        ("/api/tags", "ollama", "Ollama 模型清单", '"models"'),
    ):
        result = _fetch(transport, target + suffix, timeout, plan)
        if result is not None and result.ok and not probes.is_spa_fallback(result):
            if marker in (result.body or "") and plan.family == "unknown":
                plan.family = family
                plan.basis.append("`%s` 返回模型清单 → %s" % (result.url, label))

    return plan
