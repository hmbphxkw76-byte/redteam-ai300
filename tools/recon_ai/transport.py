#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""HTTP 传输 seam（S1）：唯一网络出口。

生产实现 `UrllibTransport` 仅用标准库 urllib；测试替身 `FakeTransport`
以路由表返回确定性响应 → 全部探测判据可离线验证（AC-23 零第三方依赖）。
"""
import json
import socket
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from typing import Dict, Optional, Tuple

DEFAULT_UA = "recon-ai/1.0 (authorized red team reconnaissance)"


@dataclass
class HttpResponse:
    """一次 HTTP 交换的原始结果；`error` 非空表示未取得响应（网络层失败）。"""

    status: int = 0
    body: str = ""
    headers: Dict[str, str] = field(default_factory=dict)
    content_type: str = ""
    error: str = ""
    elapsed_ms: int = 0

    @property
    def ok(self):
        return not self.error and 200 <= self.status < 300

    @property
    def is_json(self):
        return "json" in (self.content_type or "").lower()


class Transport:
    """传输协议（duck typing）：子类/替身实现 `request`。"""

    def request(self, method, url, json_body=None, timeout=30, stream=False):
        raise NotImplementedError

    def describe(self):
        return self.__class__.__name__


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    """显式拒绝 3xx 跟随：避免探测被引向未授权主机，且让 30x 成为可见证据。"""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class UrllibTransport(Transport):
    """生产传输：标准库 urllib，禁用重定向跟随（探测不外溢到未授权主机）。"""

    def __init__(self, user_agent=DEFAULT_UA):
        self.user_agent = user_agent
        self._opener = urllib.request.build_opener(_NoRedirect)

    def describe(self):
        return "urllib (%s)" % self.user_agent.split("/")[0]

    def request(self, method, url, json_body=None, timeout=30, stream=False):
        data = None
        headers = {"User-Agent": self.user_agent, "Accept": "*/*"}
        if json_body is not None:
            data = json.dumps(json_body).encode("utf-8")
            headers["Content-Type"] = "application/json"
        req = urllib.request.Request(url, data=data, headers=headers, method=method)
        t0 = time.time()
        try:
            with self._opener.open(req, timeout=timeout) as resp:
                raw = resp.read().decode("utf-8", "replace")
                return HttpResponse(
                    status=resp.status,
                    body=raw,
                    headers={k: v for k, v in resp.headers.items()},
                    content_type=resp.headers.get("Content-Type", ""),
                    elapsed_ms=int((time.time() - t0) * 1000),
                )
        except urllib.error.HTTPError as exc:
            # 4xx/5xx 仍是有效响应：错误语义常藏在 body（如 422 的 loc/msg）
            try:
                raw = exc.read().decode("utf-8", "replace")
            except Exception:  # pragma: no cover - 极端网络异常
                raw = ""
            return HttpResponse(
                status=exc.code,
                body=raw,
                headers={k: v for k, v in (exc.headers or {}).items()},
                content_type=(exc.headers or {}).get("Content-Type", ""),
                elapsed_ms=int((time.time() - t0) * 1000),
            )
        except (urllib.error.URLError, socket.timeout, TimeoutError, ConnectionError, OSError) as exc:
            reason = getattr(exc, "reason", exc)
            return HttpResponse(
                error=str(reason),
                elapsed_ms=int((time.time() - t0) * 1000),
            )


class FakeTransport(Transport):
    """测试替身：路由表 → 确定性响应；未命中返回 JSON 404。

    `routes` 键为 `(method, url)`，值为 `HttpResponse` 或可调用对象
    （接收 json_body 返回 HttpResponse）；亦支持按 URL 前缀匹配。
    """

    def __init__(self, routes: Optional[Dict[Tuple[str, str], object]] = None,
                 default: Optional[HttpResponse] = None):
        self.routes = dict(routes or {})
        self.default = default
        self.calls = []

    def describe(self):
        return "fake (%d routes)" % len(self.routes)

    def request(self, method, url, json_body=None, timeout=30, stream=False):
        self.calls.append((method, url, json_body))
        for key in ((method, url), (method.upper(), url), (url,)):
            if key in self.routes:
                value = self.routes[key]
                return value(json_body) if callable(value) else value
        for (m, u), value in self.routes.items():
            if isinstance(m, str) and u.endswith("*") and url.startswith(u[:-1]):
                if not m or m == method:
                    return value(json_body) if callable(value) else value
        if self.default is not None:
            return self.default
        return HttpResponse(status=404, body='{"detail":"Not Found"}',
                            content_type="application/json")


def make_transport(fake_routes=None, timeout=30):
    """工厂：传 `fake_routes` 得替身，否则得生产传输（供测试注入）。"""
    return FakeTransport(fake_routes) if fake_routes is not None else UrllibTransport()
