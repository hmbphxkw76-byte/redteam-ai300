#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""传输 seam（S1）：唯一网络出口。

生产实现 `UrllibHttpClient` 仅用标准库 urllib，禁用 3xx 跟随（探测不外溢到未授权主机）；
测试替身 `FakeHttpClient` 以路由表返回确定性响应 → 全部判据可离线验证（AC-17）。
"""
import json
import socket
import threading
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from typing import Dict, Optional
from urllib.parse import urljoin

DEFAULT_UA = "attack-mcp-tool/1.0 (authorized red team assessment)"
# MCP Streamable HTTP 要求客户端同时接受 JSON 与 SSE；缺省即符合协议，避免硬编码端点适配。
DEFAULT_ACCEPT = "application/json, text/event-stream"


@dataclass
class HttpResponse:
    """一次 HTTP 交换的结果；`error` 非空表示未取得响应（网络层失败）。"""

    status: int = 0
    body: str = ""
    headers: Dict[str, str] = field(default_factory=dict)
    content_type: str = ""
    error: str = ""
    elapsed_ms: int = 0

    @property
    def ok(self):
        return not self.error and 200 <= self.status < 300


class HttpClient:
    """传输协议（duck typing）：实现 `request` 即可替换。"""

    def request(self, method, url, json_body=None, timeout=60, headers=None):
        raise NotImplementedError

    def describe(self):
        return self.__class__.__name__


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    """显式拒绝 3xx 跟随，使 30x 成为可见证据而非被静默消化。"""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class UrllibHttpClient(HttpClient):
    """生产传输：标准库 urllib。"""

    def __init__(self, user_agent=DEFAULT_UA, extra_headers=None):
        self.user_agent = user_agent
        # 通用请求头注入：适配 Host 绑定 / 虚拟站点 / 鉴权头等同类目标，
        # 不含任何特定目标值，缺省为空。
        self.extra_headers = dict(extra_headers or {})
        self._opener = urllib.request.build_opener(_NoRedirect)

    def describe(self):
        return "urllib"

    def request(self, method, url, json_body=None, timeout=60, headers=None):
        data = None
        merged = {"User-Agent": self.user_agent, "Accept": DEFAULT_ACCEPT}
        merged.update(self.extra_headers)
        merged.update(headers or {})
        headers = merged
        if json_body is not None:
            data = json.dumps(json_body, ensure_ascii=False).encode("utf-8")
            headers["Content-Type"] = "application/json"
        req = urllib.request.Request(url, data=data, headers=headers, method=method)
        t0 = time.time()
        try:
            with self._opener.open(req, timeout=timeout) as resp:
                raw = resp.read().decode("utf-8", "replace")
                return HttpResponse(
                    status=resp.status, body=raw,
                    headers={k: v for k, v in resp.headers.items()},
                    content_type=resp.headers.get("Content-Type", ""),
                    elapsed_ms=int((time.time() - t0) * 1000))
        except urllib.error.HTTPError as exc:
            try:
                raw = exc.read().decode("utf-8", "replace")
            except Exception:  # pragma: no cover - 极端网络异常
                raw = ""
            return HttpResponse(status=exc.code, body=raw,
                                headers={k: v for k, v in (exc.headers or {}).items()},
                                content_type=(exc.headers or {}).get("Content-Type", ""),
                                elapsed_ms=int((time.time() - t0) * 1000))
        except (urllib.error.URLError, socket.timeout, TimeoutError, ConnectionError, OSError) as exc:
            return HttpResponse(error=str(getattr(exc, "reason", exc)),
                                elapsed_ms=int((time.time() - t0) * 1000))


def urllib_sse_lines(url, headers=None, timeout=30):
    """生产流读取器：GET SSE 流并按行产出（复用禁跟随 3xx 的 opener）。"""
    merged = {"User-Agent": DEFAULT_UA, "Accept": "text/event-stream"}
    merged.update(headers or {})
    req = urllib.request.Request(url, headers=merged)
    resp = urllib.request.build_opener(_NoRedirect).open(req, timeout=timeout)
    try:
        for raw in resp:
            yield raw.decode("utf-8", "replace")
    finally:
        resp.close()


class McpSseHttpClient(HttpClient):
    """旧式 HTTP+SSE MCP 传输包装（Streamable HTTP 之前的官方传输）。

    同一 `request` 契约下完成：GET 流取 `event: endpoint` 会话地址 →
    JSON-RPC POST 到该地址（服务端回 202）→ 响应从流上按 `id` 回收。
    对上层协议客户端完全透明；非 JSON-RPC 请求原样委托内层客户端。
    `stream_reader` 可注入（测试离线确定性）。
    """

    def __init__(self, inner, stream_reader=None, wait_timeout=15.0,
                 endpoint_timeout=8.0):
        self.inner = inner
        self._stream_reader = stream_reader or urllib_sse_lines
        self.wait_timeout = wait_timeout
        self.endpoint_timeout = endpoint_timeout
        self._sessions = {}
        self._lock = threading.Lock()
        self._urls = set()

    def describe(self):
        return "mcp-sse (%d session(s))" % len(self._urls)

    def _extra_headers(self):
        return dict(getattr(self.inner, "extra_headers", {}) or {})

    def request(self, method, url, json_body=None, timeout=60, headers=None):
        rpc = (method == "POST" and isinstance(json_body, dict)
               and "jsonrpc" in json_body)
        if not rpc:
            return self.inner.request(method, url, json_body=json_body,
                                      timeout=timeout, headers=headers)
        sess = self._session(url)
        if not sess["ready"].wait(self.endpoint_timeout):
            return HttpResponse(error="SSE 会话未取得 endpoint 事件")
        if sess["error"]:
            return HttpResponse(error="SSE 会话失败：%s" % sess["error"])
        if not sess["message_url"]:
            return HttpResponse(error="SSE 流未下发 endpoint 会话地址")
        message_url = urljoin(url, sess["message_url"])
        resp = self.inner.request("POST", message_url, json_body=json_body,
                                  timeout=timeout, headers=headers)
        req_id = json_body.get("id")
        if req_id is None or resp.error or not resp.ok:
            return resp
        deadline = time.time() + self.wait_timeout
        with sess["cond"]:
            while time.time() < deadline:
                for idx, evt in enumerate(sess["responses"]):
                    if evt.get("id") == req_id:
                        sess["responses"].pop(idx)
                        return HttpResponse(
                            status=200, body=json.dumps(evt, ensure_ascii=False),
                            content_type="application/json",
                            headers={"X-Transport": "mcp-sse"})
                sess["cond"].wait(max(0.05, deadline - time.time()))
        return HttpResponse(error="SSE 流等待 id=%s 响应超时" % req_id)

    def _session(self, url):
        with self._lock:
            sess = self._sessions.get(url)
            if sess is None:
                sess = {"ready": threading.Event(), "cond": threading.Condition(),
                        "message_url": "", "error": "", "responses": []}
                self._sessions[url] = sess
                self._urls.add(url)
                threading.Thread(target=self._pump, args=(url, sess),
                                 daemon=True).start()
            return sess

    def _pump(self, url, sess):
        try:
            pending = None
            for line in self._stream_reader(url, self._extra_headers(), 60):
                line = line.rstrip("\r\n")
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
                if pending == "endpoint" or (
                        payload.startswith("/") and not sess["message_url"]):
                    sess["message_url"] = payload
                    sess["ready"].set()
                else:
                    try:
                        obj = json.loads(payload)
                    except ValueError:
                        obj = None
                    if isinstance(obj, dict) and obj.get("id") is not None:
                        with sess["cond"]:
                            sess["responses"].append(obj)
                            sess["cond"].notify_all()
                pending = None
        except Exception as exc:  # noqa: BLE001 - 流断开须转为可见错误
            sess["error"] = str(getattr(exc, "reason", exc))
        finally:
            sess["ready"].set()


class FakeHttpClient(HttpClient):
    """测试替身：路由表 (`method`, `url`) 或 URL 前缀 → 确定性响应。

    值为 `HttpResponse` 或接受 `json_body` 返回 `HttpResponse` 的可调用对象；
    未命中时返回 `default`，无 `default` 则返回连接失败（模拟不可达）。
    """

    def __init__(self, routes: Optional[Dict[object, object]] = None,
                 default: Optional[HttpResponse] = None):
        self.routes = dict(routes or {})
        self.default = default
        self.calls = []

    def describe(self):
        return "fake (%d routes)" % len(self.routes)

    def request(self, method, url, json_body=None, timeout=60, headers=None):
        self.calls.append({"method": method, "url": url, "json_body": json_body,
                           "headers": headers or {}})
        for key in ((method, url), (url,)):
            if key in self.routes:
                value = self.routes[key]
                return value(json_body) if callable(value) else value
        for key, value in self.routes.items():
            if isinstance(key, tuple) and len(key) == 2 and isinstance(key[1], str) \
                    and key[1].endswith("*") and url.startswith(key[1][:-1]):
                if not key[0] or key[0] == method:
                    return value(json_body) if callable(value) else value
        if self.default is not None:
            # 与 FakeTransport 对齐：default 亦可为可调用路由处理器。
            return self.default(json_body) if callable(self.default) else self.default
        return HttpResponse(error="连接失败（假传输无匹配路由）")
