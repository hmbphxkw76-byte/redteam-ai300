#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""recon-ai 资产清单复用（SKILL.md 前置第 1 条）。

只做「读文件 + 抽端点」，不做网络。清单结构由 `recon-ai` 定义，本模块**不**
复制其契约正文（C1），只按名称宽松抽取：任何形如 `http(s)://host:port/…`、
`host:port` 的字符串，或 `host`/`port`/`url`/`endpoint` 键的组合，都视为候选端点。

抽取结果用于扩展 infra-01 的探测面（`--inventory`），避免重复枚举 recon 已知资产。
"""
import json
import os
import re
from typing import Iterable, List, Set, Tuple

URL_RE = re.compile(r"https?://[^\s\"',}]+", re.I)
HOSTPORT_RE = re.compile(r"\b([A-Za-z0-9_.\-]+):(\d{2,5})\b")
HOST_KEYS = ("host", "hostname", "ip", "address")
URL_KEYS = ("url", "endpoint", "uri", "base_url", "baseurl")


def _walk(node, out: Set[str]) -> None:
    if isinstance(node, dict):
        url = ""
        for key in URL_KEYS:
            if isinstance(node.get(key), str) and node[key].strip():
                url = node[key].strip()
                break
        host = ""
        for key in HOST_KEYS:
            if isinstance(node.get(key), str) and node[key].strip():
                host = node[key].strip()
                break
        port = node.get("port")
        if url:
            out.add(url)
        if host and isinstance(port, int):
            out.add("%s:%d" % (host, port))
        for value in node.values():
            _walk(value, out)
    elif isinstance(node, list):
        for item in node:
            _walk(item, out)
    elif isinstance(node, str):
        for match in URL_RE.finditer(node):
            out.add(match.group(0).rstrip("/"))
        for match in HOSTPORT_RE.finditer(node):
            out.add("%s:%s" % (match.group(1), match.group(2)))


def load_endpoints(path: str) -> Tuple[str, ...]:
    """从 recon 清单抽出候选端点；文件缺失或非法 JSON 返回空元组（不抛异常）。"""
    if not path or not os.path.isfile(path):
        return ()
    try:
        with open(path, encoding="utf-8") as handle:
            payload = json.load(handle)
    except (OSError, ValueError):
        return ()
    out: Set[str] = set()
    _walk(payload, out)
    return tuple(sorted(out))


def split_endpoint(value: str) -> Tuple[str, int]:
    """`host:port` / `http(s)://host:port/…` → (host, port)；无端口按 80 处理。"""
    from urllib.parse import urlparse
    text = value.strip()
    if "://" in text:
        parsed = urlparse(text)
        return (parsed.hostname or "", parsed.port or 80)
    if ":" in text:
        host, _, port = text.rpartition(":")
        return (host, int(port)) if port.isdigit() else (text, 80)
    return (text, 80)


def host_ports(values: Iterable[str]) -> Tuple[Tuple[str, int], ...]:
    """归一为去重的 (host, port) 序列，保持输入顺序。"""
    seen, out = set(), []
    for value in values:
        try:
            host, port = split_endpoint(value)
        except ValueError:
            continue
        if not host or not port:
            continue
        key = (host, port)
        if key in seen:
            continue
        seen.add(key)
        out.append(key)
    return tuple(out)


UNUSED: List = []
