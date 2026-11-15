#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""嵌入后端（可注入）：标准库确定性嵌入 + 注入点协议。

验证主面 `RagHarness` 与白盒攻击方**共享同一 embedder 实例**（白盒前提）。
生产可用任意 embedder（如 sentence-transformers），经注入点替换；核心不绑定第三方库。

确定性：分桶用 `zlib.crc32` 而非内置 `hash()`。后者对 str 受 PYTHONHASHSEED
随机化影响，跨进程不稳定，会让「同一命令重跑得到不同 top-k」——直接违反
GOVERNANCE §6.1 可复现要求，故此处不采用。
"""
import math
import re
import zlib
from typing import List, Protocol, runtime_checkable

DIM = 256
_LATIN_RE = re.compile(r"[a-z0-9]+")
_CJK_RE = re.compile(r"[\u4e00-\u9fff]+")


def tokenize(text: str) -> List[str]:
    """分词：拉丁词 + 中文单字 + 中文二元组。

    中文若按整段切分（`[\\u4e00-\\u9fff]+`）会得到整句单一词元，近义改写
    之间零重叠，检索结果退化为随机；故补单字与二元组，使「重置密码流程」与
    「密码重置步骤」仍有 4 个字元重叠，符合 RAG 检索的实际语义粒度。
    """
    low = (text or "").lower()
    tokens = _LATIN_RE.findall(low)
    for run in _CJK_RE.findall(low):
        tokens.extend(run)
        tokens.extend(run[i:i + 2] for i in range(len(run) - 1))
    return tokens


@runtime_checkable
class Embedder(Protocol):
    """注入点协议：文本 → 向量。"""

    def embed(self, text: str) -> List[float]: ...


class DeterministicEmbedder:
    """纯标准库 bag-of-tokens 嵌入；同实例被攻击方与被攻击方共享（白盒）。"""

    def __init__(self, dim: int = DIM):
        if dim <= 0:
            raise ValueError("dim 必须为正整数")
        self.dim = dim

    def embed(self, text: str) -> List[float]:
        vec = [0.0] * self.dim
        for tok in tokenize(text):
            vec[zlib.crc32(tok.encode("utf-8")) % self.dim] += 1.0
        norm = math.sqrt(sum(v * v for v in vec))
        if norm == 0:
            return vec
        return [v / norm for v in vec]


def cosine(a: List[float], b: List[float]) -> float:
    """余弦相似度；维度不一致抛 ValueError。"""
    if len(a) != len(b):
        raise ValueError("dim mismatch: %d vs %d" % (len(a), len(b)))
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(x * x for x in b))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)
