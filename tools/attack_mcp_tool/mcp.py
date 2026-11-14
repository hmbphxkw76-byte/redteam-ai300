#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""协议解释层：SSE 解析 + 两种 MCP 工具面客户端。

两种形态共用同一 `HttpClient`（传输缝），因此步骤契约与判定逻辑完全一致：
  - `JsonRpcMcpClient`：裸 MCP 端点（`tools/list` / `tools/call`，JSON-RPC 2.0）
  - `AgentSseClient`：目标 agent 会话入口（SSE 事件携带工具结果与遥测）

SSE 解析口径（AC-05）：`event:` 只作用于紧随其后的**一条** `data:`，逐行解析、
遇 data 即分发；与目标前端的解析方式一致，避免事件名跨行误归属。
"""
import json
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlsplit

from .model import Observation, ToolDescriptor, ToolSurface
from .transport import HttpClient


def api_base(target):
    """从任意入口 URL 推导 API 根（`/explore` 等 SPA 路径一律剥离）。"""
    parts = urlsplit(target if "://" in target else "http://" + target)
    host = "%s://%s" % (parts.scheme, parts.netloc)
    if parts.path.startswith("/api"):
        return host + "/api"
    return host + "/api"


def site_base(target):
    """站根（scheme://netloc），用于构造证据里的目标标识。"""
    parts = urlsplit(target if "://" in target else "http://" + target)
    return "%s://%s" % (parts.scheme, parts.netloc)


def jsonrpc_endpoint(target):
    """裸 MCP 端点：显式带路径则原样使用，否则追加 `/mcp`。"""
    parts = urlsplit(target if "://" in target else "http://" + target)
    if parts.path and parts.path != "/":
        return "%s://%s%s" % (parts.scheme, parts.netloc, parts.path)
    return "%s://%s/mcp" % (parts.scheme, parts.netloc)


@dataclass(frozen=True)
class SseEvent:
    """一条 SSE 事件。"""

    name: str
    raw: str
    obj: Optional[Any] = None


def parse_sse(text):
    """把 SSE 原文解析为事件列表（逐行分发，`event:` 只作用于下一条 data）。"""
    events: List[SseEvent] = []
    pending: Optional[str] = None
    for line in (text or "").splitlines():
        line = line.rstrip("\r")
        if line.startswith(":"):
            continue
        if line.startswith("event:"):
            pending = line[6:].strip()
            continue
        if not line.startswith("data:"):
            if not line.strip():
                pending = None
            continue
        payload = line[5:].strip()
        if not payload:
            pending = None
            continue
        name = pending or "message"
        pending = None
        try:
            obj = json.loads(payload)
        except ValueError:
            obj = None
        events.append(SseEvent(name=name, raw=payload, obj=obj))
    return events


@dataclass(frozen=True)
class Turn:
    """一次 agent 会话回合的解析结果。"""

    text: str = ""
    meta: Dict[str, Any] = field(default_factory=dict)
    results: Tuple[Observation, ...] = ()
    events: Tuple[SseEvent, ...] = ()
    status: int = 0
    request_body: Dict[str, Any] = field(default_factory=dict)
    error: str = ""

    @property
    def first_result(self):
        return self.results[0] if self.results else None

    def telemetry(self):
        for r in self.results:
            if r.telemetry:
                return r.telemetry
        return {}


class AgentSseClient:
    """目标 agent 会话入口：把提示词变成一次工具调用观测。"""

    def __init__(self, client: HttpClient, target, timeout=120):
        self.client = client
        self.target = target
        self.timeout = timeout
        self.base = api_base(target)

    def describe(self):
        return "agent-sse (%s)" % self.base

    def url_for(self, lab):
        return "%s/labs/%s/chat" % (self.base, lab)

    def probe(self, lab, prompt):
        body = {"prompt": prompt}
        url = self.url_for(lab)
        resp = self.client.request("POST", url, json_body=body, timeout=self.timeout)
        if resp.error:
            return Turn(request_body=body, error=resp.error)
        events = parse_sse(resp.body)
        meta, chunks, results = {}, [], []
        for ev in events:
            obj = ev.obj
            if not isinstance(obj, dict):
                continue
            if ev.name == "meta" and "lab_id" in obj:
                meta = obj
            elif ev.name == "mcp_result" or "tool_result" in obj:
                results.append(Observation(
                    raw=ev.raw,
                    tool_result=str(obj.get("tool_result", "")),
                    telemetry=dict(obj.get("mcp_telemetry") or {}),
                    request=body))
            elif "content" in obj:
                chunks.append(str(obj.get("content") or ""))
        return Turn(text="".join(chunks), meta=meta, results=tuple(results),
                    events=tuple(events), status=resp.status, request_body=body)

    def validate(self, lab, answer):
        """面板校验预言机：返回 (是否通过, 原始响应体)。"""
        body = {"labId": lab, "answer": answer}
        resp = self.client.request("POST", "%s/secrets/validate" % self.base,
                                   json_body=body, timeout=30)
        if resp.error:
            return False, resp.error
        try:
            data = json.loads(resp.body)
        except ValueError:
            return False, resp.body
        return bool(data.get("success")), resp.body


class JsonRpcMcpClient:
    """裸 MCP 端点客户端（JSON-RPC 2.0）。"""

    def __init__(self, client: HttpClient, target, timeout=30):
        self.client = client
        self.endpoint = jsonrpc_endpoint(target)
        self.timeout = timeout
        self._seq = 0

    def describe(self):
        return "jsonrpc (%s)" % self.endpoint

    def _call(self, method, params=None):
        self._seq += 1
        body = {"jsonrpc": "2.0", "id": self._seq, "method": method}
        if params is not None:
            body["params"] = params
        resp = self.client.request("POST", self.endpoint, json_body=body,
                                   timeout=self.timeout)
        return body, resp

    def list_tools(self):
        """`tools/list` → (工具面, 观测)。协议错误时工具面为空且观测带 error。"""
        body, resp = self._call("tools/list", {})
        obs = Observation(raw=resp.body, request=body, error=resp.error)
        if resp.error:
            return ToolSurface(source="jsonrpc"), obs
        try:
            data = json.loads(resp.body)
        except ValueError:
            return ToolSurface(source="jsonrpc"), Observation(
                raw=resp.body, request=body, error="响应非 JSON")
        if "error" in data:
            return ToolSurface(source="jsonrpc"), Observation(
                raw=resp.body, request=body,
                error="协议错误：%s" % data["error"].get("message", data["error"]))
        tools = []
        for item in (data.get("result") or {}).get("tools") or []:
            tools.append(ToolDescriptor(
                name=str(item.get("name", "")),
                server_id=str(item.get("_server_id") or item.get("server_id") or ""),
                description=str(item.get("description", "")),
                scope=str(item.get("_scope") or item.get("scope") or ""),
                trust=str(item.get("_trust") or item.get("trust") or "")))
        return ToolSurface(tools=tuple(tools), source="jsonrpc"), Observation(
            raw=resp.body, request=body,
            text=json.dumps([t.as_dict() for t in tools], ensure_ascii=False, indent=1))

    def call_tool(self, name, arguments=None):
        """`tools/call` → 观测（`tool_result` 取首个文本内容）。"""
        body, resp = self._call("tools/call", {"name": name,
                                               "arguments": arguments or {}})
        if resp.error:
            return Observation(raw=resp.body, request=body, error=resp.error)
        try:
            data = json.loads(resp.body)
        except ValueError:
            return Observation(raw=resp.body, request=body, error="响应非 JSON")
        if "error" in data:
            return Observation(raw=resp.body, request=body,
                               error="协议错误：%s" % data["error"].get("message", data["error"]))
        result = data.get("result") or {}
        parts = []
        for item in result.get("content") or []:
            if isinstance(item, dict) and item.get("type") == "text":
                parts.append(str(item.get("text", "")))
        text = "\n".join(parts) if parts else json.dumps(result, ensure_ascii=False)
        return Observation(raw=resp.body, request=body, text=text,
                           tool_result=text,
                           telemetry={"is_error": bool(result.get("isError")),
                                      "policy_decision": "allowed"})
