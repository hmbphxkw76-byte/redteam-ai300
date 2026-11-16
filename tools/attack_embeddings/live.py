#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""真实目标适配层（核实闸 C-1 / C-2）。

仅用标准库 `urllib`，保持仓库「零外部依赖」纪律；真实 embedder 与向量库
通过本层接入，夹具（`harness.py`）在无现场条件时提供确定性等价面。

两类适配器：
  - `LiveEmbeddingClient`：OpenAI 兼容 `POST {base}/v1/embeddings`（`{"input": ...}`）；
    亦支持 `GET {base}/v1/models` 枚举。
  - `LiveVectorStoreClient`：HTTP JSON 检索 `POST {store}`（`{"vector": [...], "top_k": k}`）
    或 `{"query": "<text>", "top_k": k}`；返回 `{"matches": [{"id","score","text"}]}`。

失败一律抛 `LiveError`，由 CLI 明确报错并以非零码退出——**不静默降级**，
避免把「未连通」误报为「攻击未生效」（GOVERNANCE §6 如实记录原则）。
"""
import json
import urllib.error
import urllib.request
from typing import Dict, List, Optional


class LiveError(RuntimeError):
    """真实目标不可达或响应不符合约定。"""


def _post_json(url: str, payload: dict, timeout: float = 10.0,
               headers: Optional[Dict[str, str]] = None) -> dict:
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=body, method="POST")
    req.add_header("Content-Type", "application/json")
    for k, v in (headers or {}).items():
        req.add_header(k, v)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8", "replace")
    except (urllib.error.URLError, OSError) as exc:
        raise LiveError("POST %s 失败：%s" % (url, exc)) from exc
    try:
        return json.loads(raw)
    except ValueError as exc:
        raise LiveError("POST %s 返回非 JSON：%r" % (url, raw[:200])) from exc


def _get_json(url: str, timeout: float = 10.0,
              headers: Optional[Dict[str, str]] = None) -> dict:
    req = urllib.request.Request(url, method="GET")
    for k, v in (headers or {}).items():
        req.add_header(k, v)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8", "replace")
    except (urllib.error.URLError, OSError) as exc:
        raise LiveError("GET %s 失败：%s" % (url, exc)) from exc
    try:
        return json.loads(raw)
    except ValueError as exc:
        raise LiveError("GET %s 返回非 JSON：%r" % (url, raw[:200])) from exc


class LiveEmbeddingClient:
    """OpenAI 兼容 embedding 端点客户端（emb-01/emb-02/emb-03/emb-04/emb-05）。"""

    def __init__(self, base_url: str, model: str = "text-embedding-3-small",
                 api_key: Optional[str] = None, timeout: float = 10.0):
        if not (base_url or "").strip():
            raise LiveError("必须提供 --endpoint")
        self.base = base_url.rstrip("/")
        self.model = model
        self.timeout = timeout
        self.headers = {"Authorization": "Bearer %s" % api_key} if api_key else {}

    def list_models(self) -> List[str]:
        """emb-01：枚举可查询模型清单。"""
        data = _get_json(self.base + "/v1/models", self.timeout, self.headers)
        items = data.get("data") if isinstance(data, dict) else None
        if not isinstance(items, list):
            raise LiveError("GET /v1/models 响应缺少 data 数组")
        out = []
        for it in items:
            if isinstance(it, dict) and it.get("id"):
                out.append(str(it["id"]))
            elif isinstance(it, str):
                out.append(it)
        return out

    def embed(self, text: str) -> List[float]:
        """emb-02：提交文本，返回维度与向量。"""
        if not (text or "").strip():
            raise LiveError("空文本无法提交")
        data = _post_json(self.base + "/v1/embeddings",
                          {"model": self.model, "input": text},
                          self.timeout, self.headers)
        try:
            vec = data["data"][0]["embedding"]
        except (KeyError, IndexError, TypeError) as exc:
            raise LiveError("POST /v1/embeddings 响应缺少 data[0].embedding") from exc
        if not isinstance(vec, list) or not vec:
            raise LiveError("embedding 非非空数组")
        return [float(x) for x in vec]

    def dimension(self, text: str = "probe") -> int:
        return len(self.embed(text))


class LiveVectorStoreClient:
    """HTTP 暴露的向量库检索客户端（emb-06）。"""

    def __init__(self, store_url: str, timeout: float = 10.0,
                 api_key: Optional[str] = None):
        if not (store_url or "").strip():
            raise LiveError("必须提供 --store")
        self.url = store_url
        self.timeout = timeout
        self.headers = {"Authorization": "Bearer %s" % api_key} if api_key else {}

    def query_vector(self, vector: List[float], top_k: int = 5) -> List[dict]:
        data = _post_json(self.url, {"vector": list(vector), "top_k": int(top_k)},
                          self.timeout, self.headers)
        return _normalize_matches(data)

    def query_text(self, text: str, top_k: int = 5) -> List[dict]:
        data = _post_json(self.url, {"query": text, "top_k": int(top_k)},
                          self.timeout, self.headers)
        return _normalize_matches(data)


def _normalize_matches(data: object) -> List[dict]:
    """把多种常见响应形状归一为 [{id, sim, text}]。"""
    if isinstance(data, dict):
        raw = data.get("matches") or data.get("results") or data.get("documents") or []
    elif isinstance(data, list):
        raw = data
    else:
        raw = []
    out: List[dict] = []
    for it in raw:
        if not isinstance(it, dict):
            continue
        out.append({
            "id": str(it.get("id", it.get("doc_id", ""))),
            "sim": float(it.get("score", it.get("similarity", 0.0)) or 0.0),
            "text": str(it.get("text", it.get("content", ""))),
        })
    return out
