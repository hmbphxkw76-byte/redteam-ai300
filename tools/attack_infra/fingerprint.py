#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""指纹表与三元组判据（纯函数，不含 IO）。

判据来源（canonical）：F-2/F-3/F-4/F-5/F-9/F-10/F-11/F-12 与陷阱 P-1/P-3。
「HTTP 200」不构成存在性证明——80 端口任意路径返回 `200 text/html`；
故存在性 = 状态码 2xx + `Content-Type` 含 json/纯文本 + **响应结构命中指纹键**。
"""
from dataclasses import dataclass
from typing import Optional, Sequence, Tuple
from urllib.parse import urlparse

from .transport import HttpResponse

JSON_MODELS = "json_models"
OLLAMA_TAGS = "ollama_tags"
K8S_VERSION = "k8s_version"
LITELLM_HEALTH = "litellm_health"
GITLAB_VERSION = "gitlab_version"
FLANNEL_HEALTHZ = "flannel_healthz"
EMPTY_OK = "empty_ok"
HTML = "html"
AUTH = "auth"

TLS_PORTS: Tuple[int, ...] = (6443, 10250)


@dataclass(frozen=True)
class Probe:
    """一条探测定义：路径 + 期望结构 + 默认端口候选。"""

    kind: str
    path: str
    shapes: Tuple[str, ...]
    ports: Tuple[int, ...]
    method: str = "GET"


CANDIDATE_PORTS: dict = {
    "vllm": (8000,),
    "triton": (8000,),
    "litellm": (4000,),
    "ollama": (11434,),
    "k8s_apiserver": (6443,),
    "kubelet": (10250,),
    "gitlab": (8080,),
    "flannel": (8081,),
}

PROBES: Tuple[Probe, ...] = (
    Probe("ollama", "/api/tags", (OLLAMA_TAGS,), (11434,)),
    Probe("ollama", "/v1/models", (JSON_MODELS,), (11434,)),
    Probe("vllm", "/v1/models", (JSON_MODELS,), (8000,)),
    Probe("triton", "/v2/health/ready", (EMPTY_OK,), (8000,)),
    Probe("litellm", "/health", (LITELLM_HEALTH, EMPTY_OK), (4000,)),
    Probe("k8s_apiserver", "/version", (K8S_VERSION,), (6443,)),
    Probe("kubelet", "/healthz", (EMPTY_OK, AUTH), (10250,)),
    Probe("gitlab", "/api/v4/version", (GITLAB_VERSION, AUTH), (8080,)),
    Probe("flannel", "/healthz", (FLANNEL_HEALTHZ,), (8081,)),
)

ALL_PORTS: Tuple[int, ...] = tuple(sorted({p for probe in PROBES for p in probe.ports}))


def is_auth_status(resp: HttpResponse) -> bool:
    return resp.status in (401, 403)


def shape_of(resp: HttpResponse) -> str:
    """把响应归约为结构形状；无法归约返回空串（判 ABSENT）。"""
    if resp.error:
        return ""
    if is_auth_status(resp):
        return AUTH
    if not (200 <= resp.status < 300):
        return ""
    ctype = (resp.content_type or "").lower()
    if "html" in ctype:
        return HTML
    body = (resp.body or "").strip()
    if resp.is_json or body.startswith("{"):
        payload = resp.json()
        if isinstance(payload, dict):
            if payload.get("object") == "list" and isinstance(payload.get("data"), list):
                return JSON_MODELS
            if isinstance(payload.get("models"), list):
                return OLLAMA_TAGS
            if "healthy" in payload:
                return LITELLM_HEALTH
            if "gitVersion" in payload:
                return K8S_VERSION
            if "version" in payload and "revision" in payload:
                return GITLAB_VERSION
            if payload.get("kind") == "Status":
                return AUTH
        return ""
    if "flanneld" in body.lower():
        return FLANNEL_HEALTHZ
    if body == "" or body.lower() in ("ok", "ok\n", "ready", "live"):
        return EMPTY_OK
    return ""


def classify(probe: Probe, resp: HttpResponse) -> str:
    """命中返回服务类型，未命中返回空串。"""
    shape = shape_of(resp)
    if shape and shape in probe.shapes:
        return probe.kind
    return ""


def detect(resp: HttpResponse) -> Optional[str]:
    """不依赖路径的结构标签（供报告与调试使用）。"""
    shape = shape_of(resp)
    return shape or None


def scheme_for(port: int) -> str:
    return "https" if port in TLS_PORTS else "http"


def normalize_target(target: str) -> str:
    """把 `host` / `host:port` / `http(s)://host[:port]` 归一为 host。"""
    text = (target or "").strip()
    if not text:
        raise ValueError("target 不能为空")
    if "://" not in text:
        text = "http://" + text
    parsed = urlparse(text)
    host = parsed.hostname or ""
    if not host:
        raise ValueError("无法解析 target: %r" % (target,))
    return host


def endpoint_url(host: str, port: int, path: str) -> str:
    return "%s://%s:%d%s" % (scheme_for(port), host, port, path)


def probe_targets(target: str, ports: Optional[Sequence[int]] = None):
    """生成 (port, path, url) 候选；默认覆盖全部指纹端口。"""
    host = normalize_target(target)
    selected = tuple(ports) if ports else ALL_PORTS
    out = []
    for port in selected:
        for probe in PROBES:
            if probe.ports != (port,) and port not in probe.ports:
                continue
            out.append((port, probe.path, endpoint_url(host, port, probe.path)))
    return out


def probes_for_port(port: int) -> Tuple[Probe, ...]:
    """该端口的探测集合；未知端口回退为全量路径（recon 清单可能给出任意端口）。"""
    known = tuple(p for p in PROBES if port in p.ports)
    return known or PROBES
