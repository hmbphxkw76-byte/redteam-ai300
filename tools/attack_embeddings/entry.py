#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""CLI 入口共用工具：向量文件读写、夹具构建、统一输出与错误码。

设计意图：4 个 SKILL.md 点名的脚本（`embed_invert` / `membership_inference` /
`adv_embed` / `vector_lookup`）只做参数解析与结果渲染，逻辑全部落在这里与
`attacks.py`，避免四份重复代码漂移（深层模块原则）。
"""
import json
import os
import sys
from typing import Dict, List, Optional

EXIT_OK = 0
EXIT_BAD_INPUT = 2
EXIT_UNREACHABLE = 3


def repo_root() -> str:
    """返回仓库根（tools/attack_embeddings/entry.py → 上两级）。"""
    return os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def bootstrap() -> None:
    """把仓库根加入 sys.path，使 `python tools/<script>.py` 与 `-m` 共用同一模块身份。"""
    root = repo_root()
    if root not in sys.path:
        sys.path.insert(0, root)


def parse_floats(text: str) -> List[float]:
    """解析向量：支持 JSON 数组或逗号/空白分隔。"""
    text = (text or "").strip()
    if not text:
        raise ValueError("空向量文本")
    if text[0] in "[(":
        data = json.loads(text)
        if not isinstance(data, list):
            raise ValueError("JSON 向量须为数组")
        return [float(x) for x in data]
    tokens = [t for t in text.replace(",", " ").split() if t]
    return [float(t) for t in tokens]


def load_vector(path: str) -> List[float]:
    """从文件或 `-`（stdin）读取向量。"""
    if path == "-":
        return parse_floats(sys.stdin.read())
    with open(path, encoding="utf-8") as f:
        return parse_floats(f.read())


def save_vector(path: str, vec: List[float]) -> None:
    """写出向量为 JSON 数组（供 `--vec out.vec` 与后续步骤复用）。"""
    with open(path, "w", encoding="utf-8") as f:
        json.dump([round(float(x), 6) for x in vec], f)


def load_json(path: str) -> object:
    """读取 JSON 文件；`-` 表示 stdin。"""
    if path == "-":
        return json.loads(sys.stdin.read())
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def emit(payload: Dict[str, object]) -> None:
    """统一输出：人类可读摘要行 + 完整 JSON 块（同一事实，机读不丢字段）。"""
    for key in ("step", "mode", "target", "verdict"):
        if key in payload:
            print("%s: %s" % (key, payload[key]))
    print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))


def fail(message: str, code: int = EXIT_BAD_INPUT) -> int:
    """错误统一走 stderr，并返回可判定的退出码。"""
    print("ERROR: %s" % message, file=sys.stderr)
    return code


def fixture_harness(corpus: Optional[Dict[str, str]] = None):
    """构建确定性夹具 harness（零外部依赖，本地验证面）。"""
    from .harness import EmbeddingHarness, fixture_corpus
    h = EmbeddingHarness()
    h.ingest(corpus if corpus is not None else fixture_corpus())
    return h


def harness_from_corpus_file(path: Optional[str]):
    """从 JSON `{doc_id: text}` 文件构建夹具向量库；缺省用内置语料。"""
    if not path:
        return fixture_harness()
    data = load_json(path)
    if not isinstance(data, dict):
        raise ValueError("语料文件须为 {doc_id: text} 的 JSON 对象")
    return fixture_harness({str(k): str(v) for k, v in data.items()})
