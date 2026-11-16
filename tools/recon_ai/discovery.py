#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""自适应发现（S4）：入口 → 应用族/基路径/版本 → 追加类端点证据。

只做被动 GET，请求上限 `MAX_DISCOVERY_REQUESTS`，不改变 7 步判据语义；
发现结果并入 recon-03 的证据片段，判据按需扫描（不新增资产类别）。
"""
import re
import time
from dataclasses import dataclass, field
from typing import List
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
                "basis": list(self.basis), "tried": self.tried()}


def _fetch(transport, url, timeout, plan, json_body=None, method="GET"):
    """发一次发现请求并记录；任何异常都转为 error 结果，不中断发现。"""
    if len(plan.results) >= MAX_DISCOVERY_REQUESTS:
        return None
    result = ProbeResult(step_id="recon-03", url=url, method=method,
                         command=probes.curl_command(method, url, json_body),
                         request_body=dict(json_body or {}), note="discovery")
    t0 = time.time()
    try:
        resp = transport.request(method, url, json_body, timeout=timeout)
    except Exception as exc:
        result.error = "传输异常：%s" % exc
        result.elapsed_ms = int((time.time() - t0) * 1000)
        plan.results.append(result)
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
    plan.results.append(result)
    return result


def _candidate_bases(body):
    """从入口页链接提取浅层基路径候选（排除静态文件与深层路径）。"""
    out = []
    for href in HREF_RE.findall(body or "")[:80]:
        if not href.startswith("/") or href.startswith("//"):
            continue
        path = href.split("#")[0].split("?")[0].rstrip("/")
        if not path or path == "/" or path.count("/") > 2:
            continue
        if re.search(r"\.(?:html?|js|css|png|jpe?g|gif|svg|json|md)$", path, re.I):
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

    bases = [""] + _candidate_bases(root.body)
    for base in bases[:3]:
        health = _fetch(transport, _join(target, base, "/_stcore/health"), timeout, plan)
        if _is_health_ok(health):
            plan.family = "streamlit"
            plan.base_path = base
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
            plan.basis.append("`/_stcore/host-config` 可匿名读取（HTTP %d）"
                              % host_config.status)
        if plan.version:
            plan.basis.append("前端产物标识版本 `%s`" % plan.version)

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
                plan.family = plan.family if plan.family != "unknown" else "gradio"
                plan.basis.append("`%s` 返回组件配置 → Gradio" % result.url)
            elif family == "openapi" and '"openapi"' in (result.body or ""):
                plan.family = plan.family if plan.family != "unknown" else "openapi"
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
