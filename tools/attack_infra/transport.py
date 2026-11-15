#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""seam ①：HTTP 传输（唯一网络出口）。

默认**绕开环境代理**（AC-02）：urllib 的默认 opener 会读取 `HTTP_PROXY`
等变量，在本机将探测变成代理回显（canonical F-14 陷阱），故显式注入空
`ProxyHandler({})`。TLS 校验默认关闭以适配自签证书目标（红队场景）。

网络层失败统一返回 `error` 非空、`status=0`，不抛异常（设计记录 §2）。
"""
import json
import socket
import ssl
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Optional, Tuple

DEFAULT_UA = "attack-infra/1.0 (authorized red team infrastructure assessment)"


@dataclass
class HttpResponse:
    status: int = 0
    body: str = ""
    headers: Dict[str, str] = field(default_factory=dict)
    content_type: str = ""
    error: str = ""
    elapsed_ms: int = 0

    @property
    def ok(self) -> bool:
        return not self.error and 200 <= self.status < 300

    @property
    def is_json(self) -> bool:
        return "json" in (self.content_type or "").lower()

    def json(self) -> Optional[Any]:
        if not self.body:
            return None
        try:
            return json.loads(self.body)
        except (ValueError, TypeError):
            return None


class Transport:
    """传输协议（duck typing）。"""

    def request(self, method, url, json_body=None, headers=None, timeout=None):
        raise NotImplementedError

    def describe(self) -> str:
        return self.__class__.__name__


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    """不跟随重定向：3xx 必须作为事实被记录，不得被后续 200 掩盖（P-1）。"""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def _ssl_context(verify_tls: bool):
    if verify_tls:
        return ssl.create_default_context()
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    return ctx


class UrllibTransport(Transport):
    """生产实现：仅标准库；显式空代理 + TLS 可配。"""

    def __init__(self, timeout=30, user_agent=DEFAULT_UA, verify_tls=False):
        self.timeout = timeout
        self.user_agent = user_agent
        self.verify_tls = verify_tls
        self._opener = urllib.request.build_opener(
            urllib.request.ProxyHandler({}),
            _NoRedirect(),
            urllib.request.HTTPSHandler(context=_ssl_context(verify_tls)),
        )

    def describe(self) -> str:
        return "urllib(proxy=off,tls_verify=%s)" % self.verify_tls

    def request(self, method, url, json_body=None, headers=None, timeout=None):
        data = None
        hdrs = {"User-Agent": self.user_agent, "Accept": "*/*"}
        if json_body is not None:
            data = json.dumps(json_body).encode("utf-8")
            hdrs["Content-Type"] = "application/json"
        hdrs.update(headers or {})
        req = urllib.request.Request(url, data=data, headers=hdrs, method=method.upper())
        started = time.time()
        try:
            with self._opener.open(req, timeout=timeout or self.timeout) as resp:
                body = resp.read().decode("utf-8", "replace")
                return HttpResponse(
                    status=resp.status,
                    body=body,
                    headers={k.lower(): v for k, v in resp.headers.items()},
                    content_type=resp.headers.get("Content-Type", "") or "",
                    elapsed_ms=int((time.time() - started) * 1000),
                )
        except urllib.error.HTTPError as exc:
            body = ""
            try:
                body = exc.read().decode("utf-8", "replace")
            except Exception:  # pragma: no cover - 读取失败不影响状态码事实
                body = ""
            return HttpResponse(
                status=exc.code,
                body=body,
                headers={k.lower(): v for k, v in (exc.headers or {}).items()},
                content_type=(exc.headers or {}).get("Content-Type", "") or "",
                elapsed_ms=int((time.time() - started) * 1000),
            )
        except (urllib.error.URLError, socket.timeout, OSError, ssl.SSLError) as exc:
            return HttpResponse(error=_short_error(exc),
                                elapsed_ms=int((time.time() - started) * 1000))


def _short_error(exc: Exception) -> str:
    reason = getattr(exc, "reason", None)
    text = str(reason if reason is not None else exc) or exc.__class__.__name__
    return text[:200]


class FakeTransport(Transport):
    """测试替身：路由表驱动，`"GET http://h:p/path"` → HttpResponse 或可调用对象。"""

    def __init__(self, routes: Dict[str, Any], default: Optional[HttpResponse] = None):
        self.routes = dict(routes)
        self.default = default or HttpResponse(error="no route")
        self.calls: list = []

    def describe(self) -> str:
        return "fake(%d routes)" % len(self.routes)

    def request(self, method, url, json_body=None, headers=None, timeout=None):
        key = "%s %s" % (method.upper(), url)
        self.calls.append((key, json_body))
        value = self.routes.get(key, self.default)
        if isinstance(value, HttpResponse):
            return value
        if callable(value):
            return value(method, url, json_body)
        return HttpResponse(**value)

    def methods(self) -> Tuple[str, ...]:
        return tuple(call[0].split(" ", 1)[0] for call in self.calls)

    def called_paths(self) -> Tuple[str, ...]:
        return tuple(call[0].split(" ", 1)[1] for call in self.calls if " " in call[0])
