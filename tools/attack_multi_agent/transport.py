#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""传输缝（S3）：HTTP 客户端抽象，生产用 urllib，单测注入替身即离线（AC-14）。

不引入第三方 HTTP 库；`pyrit` 等重依赖仅在 `pyrit_attack.py` 内懒导入，
本模块与运行时对象图构造解耦（B7）。
"""
import json
import urllib.request
from dataclasses import dataclass
from typing import Dict, Optional


@dataclass
class Response:
    """一次 HTTP 调用的归一化结果。"""

    status: int
    body: str
    content_type: str
    error: str = ""

    def ok(self):
        return self.status == 200 and not self.error


class HttpClient:
    """传输协议：实现 `request` 即可替换（测试注入 `FakeHttpClient`）。"""

    def request(self, method, url, body=None, timeout=15, headers=None):
        raise NotImplementedError

    def describe(self):
        return self.__class__.__name__


class UrllibHttpClient(HttpClient):
    """生产实现：标准库 urllib。"""

    def request(self, method, url, body=None, timeout=15, headers=None):
        headers = headers or {"Content-Type": "application/json"}
        data = None
        if body is not None:
            data = body if isinstance(body, bytes) else json.dumps(body, ensure_ascii=False).encode("utf-8")
        req = urllib.request.Request(url, data=data, method=method.upper())
        for k, v in headers.items():
            req.add_header(k, v)
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                raw = resp.read().decode("utf-8", "replace")
                ctype = resp.headers.get("Content-Type", "")
                return Response(resp.status, raw, ctype)
        except urllib.error.HTTPError as exc:
            raw = exc.read().decode("utf-8", "replace") if exc.fp else ""
            return Response(exc.code, raw, exc.headers.get("Content-Type", ""), error=str(exc))
        except (OSError, ValueError) as exc:
            return Response(0, "", "", error=str(exc))


class FakeHttpClient(HttpClient):
    """测试替身：按 URL 前缀脚本化返回，并记录调用（用于断言证据契约）。"""

    def __init__(self, script=None, default=None):
        self.script = script or {}      # url-prefix -> Response
        self.default = default or Response(200, "", "")
        self.calls = []

    def request(self, method, url, body=None, timeout=15, headers=None):
        self.calls.append({"method": method, "url": url, "body": body})
        for prefix, resp in self.script.items():
            if url.startswith(prefix):
                return resp
        return self.default

    def describe(self):
        return "fake"
