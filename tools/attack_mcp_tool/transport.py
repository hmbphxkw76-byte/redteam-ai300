#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""传输 seam（S1）：唯一网络出口。

生产实现 `UrllibHttpClient` 仅用标准库 urllib，禁用 3xx 跟随（探测不外溢到未授权主机）；
测试替身 `FakeHttpClient` 以路由表返回确定性响应 → 全部判据可离线验证（AC-17）。
"""
import json
import socket
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from typing import Dict, Optional

DEFAULT_UA = "attack-mcp-tool/1.0 (authorized red team assessment)"


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

    def request(self, method, url, json_body=None, timeout=60):
        raise NotImplementedError

    def describe(self):
        return self.__class__.__name__


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    """显式拒绝 3xx 跟随，使 30x 成为可见证据而非被静默消化。"""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class UrllibHttpClient(HttpClient):
    """生产传输：标准库 urllib。"""

    def __init__(self, user_agent=DEFAULT_UA):
        self.user_agent = user_agent
        self._opener = urllib.request.build_opener(_NoRedirect)

    def describe(self):
        return "urllib"

    def request(self, method, url, json_body=None, timeout=60):
        data = None
        headers = {"User-Agent": self.user_agent, "Accept": "*/*"}
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

    def request(self, method, url, json_body=None, timeout=60):
        self.calls.append({"method": method, "url": url, "json_body": json_body})
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
            return self.default
        return HttpResponse(error="连接失败（假传输无匹配路由）")
