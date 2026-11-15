#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""路径 A 第 1 步的写入面：摄取通道 / 向量库直写（SKILL.md 路径 A）。

SKILL.md 给了两条写入口：内容摄取 API（`curl -X POST <RAG_INGEST> -d '{"doc":…}'`）
与已立足点时的直接写入（`inject_kb.py --target <VECTOR_DB> --doc …`）。
本模块把两者抽象为同一 `IngestChannel` 协议，只返回**可观察回执**
（通道 / 状态 / 响应原文 / 是否落库），供证据「关键输出」直接引用。

只读或不可达时一律返回 `delivered=False` 并附判定依据，由上层的
「失败与豁免」分支改走间接注入——不伪装成功，也不阻断其余路径。
"""
import json
import os
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any, Callable, Optional

DEFAULT_PAYLOAD_KEY = "doc"


@dataclass(frozen=True)
class IngestResult:
    """一次写入的可观察回执。"""

    delivered: bool
    channel: str
    status: str = ""
    response: str = ""
    reason: str = ""

    def render(self) -> str:
        tail = ("\n判定依据: %s" % self.reason) if self.reason else ""
        return ("通道: %s\n状态: %s\n响应: %s\n落库: %s%s"
                % (self.channel, self.status or "—",
                   (self.response or "（无）").strip()[:400],
                   "是" if self.delivered else "否", tail))

    def as_dict(self):
        return {"channel": self.channel, "delivered": self.delivered,
                "status": self.status, "response": self.response,
                "reason": self.reason}


def _from_http(code: int, body: str, channel: str) -> IngestResult:
    """HTTP 状态码 → 是否落库；4xx/5xx 如实记为未写入。"""
    delivered = 200 <= code < 300
    reason = ""
    if not delivered:
        if code in (401, 403):
            reason = "HTTP %d：摄取端点拒绝写入（只读或无权限）" % code
        elif code == 404:
            reason = "HTTP 404：摄取端点不存在"
        elif code == 405:
            reason = "HTTP 405：端点不允许 POST（无写入通道）"
        else:
            reason = "HTTP %d：写入未成功" % code
    return IngestResult(delivered, channel, str(code), body, reason)


def _default_opener(request, timeout):
    """默认走 urllib；返回 (status, body)。测试经 `opener` 注入替身，不联网。"""
    with urllib.request.urlopen(request, timeout=timeout) as resp:
        return int(getattr(resp, "status", 200)), resp.read().decode("utf-8", "replace")


class HttpIngestChannel:
    """内容摄取 API 通道（SKILL.md 路径 A 的 `curl -X POST <RAG_INGEST>` 等价物）。"""

    name = "ingest-api"

    def __init__(self, url: str, timeout: float = 5.0,
                 payload_key: str = DEFAULT_PAYLOAD_KEY,
                 opener: Optional[Callable[[Any, float], Any]] = None):
        if not (url or "").strip():
            raise ValueError("HttpIngestChannel 需要摄取端点 URL")
        self.url = url.strip()
        self.timeout = timeout
        self.payload_key = payload_key
        self.opener = opener or _default_opener
        self.requests = []

    def put(self, doc_id: str, text: str) -> IngestResult:
        payload = {self.payload_key: text, "id": doc_id}
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        request = urllib.request.Request(
            self.url, data=data, method="POST",
            headers={"Content-Type": "application/json"})
        self.requests.append(payload)
        try:
            code, body = self.opener(request, self.timeout)
        except urllib.error.HTTPError as exc:  # 4xx/5xx：端点存在但拒绝
            return _from_http(int(exc.code), str(exc.reason or ""), self.name)
        except urllib.error.URLError as exc:   # 不可达：无写入通道
            return IngestResult(False, self.name, "unreachable", "",
                                "摄取端点不可达：%s" % (exc.reason or exc))
        except OSError as exc:
            return IngestResult(False, self.name, "error", "",
                                "摄取请求失败：%s" % exc)
        return _from_http(int(code), str(body), self.name)


class FileIngestChannel:
    """向量库/语料直写通道（已立足点）：以 JSONL 落盘模拟直接写入。"""

    name = "direct-write"

    def __init__(self, path: str, prefix: str = "mal"):
        if not (path or "").strip():
            raise ValueError("FileIngestChannel 需要写入路径")
        if os.path.isdir(path):
            raise ValueError("写入路径是目录：%s（须为文件）" % path)
        self.path = path
        self.prefix = prefix

    def put(self, doc_id: str, text: str) -> IngestResult:
        record = {"id": "%s-%s" % (self.prefix, doc_id), "doc": text}
        try:
            parent = os.path.dirname(os.path.abspath(self.path))
            if parent and not os.path.isdir(parent):
                os.makedirs(parent, exist_ok=True)
            with open(self.path, "a", encoding="utf-8") as handle:
                handle.write(json.dumps(record, ensure_ascii=False) + "\n")
        except OSError as exc:
            return IngestResult(False, self.name, "error", "",
                                "直写失败：%s" % exc)
        return IngestResult(True, self.name, "appended",
                            "已写入 %s（%d 字节）" % (self.path, len(text)))


class FakeIngestChannel:
    """离线/测试替身：按预设回执返回，记录全部请求参数。"""

    name = "fake-ingest"

    def __init__(self, delivered: bool = True, status: str = "200",
                 response: Optional[str] = None, reason: str = ""):
        self.delivered = delivered
        self.status = status
        self.response = response if response is not None else "{\"ok\": true}"
        self.reason = reason
        self.calls = []

    def put(self, doc_id: str, text: str) -> IngestResult:
        self.calls.append((doc_id, text))
        return IngestResult(self.delivered, self.name, self.status,
                            self.response, self.reason)


class ReadOnlyChannel:
    """只读判定通道：显式记录「无写入通道」的判定依据（豁免分支入口）。"""

    name = "read-only"

    def __init__(self, reason: str = "目标 RAG 只读：无摄取端点、无向量库写权限"):
        self.reason = reason

    def put(self, doc_id: str, text: str) -> IngestResult:
        return IngestResult(False, self.name, "read-only", "", self.reason)


def read_doc(path: str) -> str:
    """读取待注入文档正文（`--doc` 参数）。"""
    if not os.path.isfile(path):
        raise ValueError("文档不存在：%s" % path)
    with open(path, encoding="utf-8") as handle:
        text = handle.read().strip()
    if not text:
        raise ValueError("文档为空：%s" % path)
    return text


def channel_for(url: str = "", store: str = "",
                writable: str = "unknown") -> Optional[Any]:
    """按可用写入面选择通道；无任何写入口返回 None（由上层决定豁免）。"""
    if (url or "").strip():
        return HttpIngestChannel(url)
    if (store or "").strip():
        return FileIngestChannel(store)
    if writable == "no":
        return ReadOnlyChannel()
    return None
