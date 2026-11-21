#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""S5 导出 seam：向量库 → .npy/.csv/.parquet 三格式（Ch6 §6.2 Listing 3–4，AC-C1）。

零第三方依赖（ADR-0003）：
  - .npy  用标准库手写 NumPy v1.0 格式（magic + header + float32 raw bytes）；
  - .csv  用标准库 csv；
  - .parquet 需 pyarrow；不可用时显式 NOT_AVAILABLE，不静默伪造格式（对齐 live.py 失败不静默原则）。

数据来源可为：
  - 内存向量序列（夹具/已导出列表）；
  - 经注入的 ``fetch_page`` 回调（游标分页，模拟 GraphQL cursor-based pagination）。

公开入口：``export_vectors`` / ``write_npy`` / ``write_csv`` / ``try_write_parquet``。
"""
from __future__ import annotations

import csv
import os
import struct
from typing import Callable, Dict, List, Optional, Sequence

NPY_MAGIC = b"\x93NUMPY"
NPY_VERSION = (1, 0)


def _float32_bytes(values: Sequence[float]) -> bytes:
    return b"".join(struct.pack("<f", float(v)) for v in values)


def write_npy(path: str, matrix: Sequence[Sequence[float]]) -> Dict[str, object]:
    """写标准 NumPy .npy v1.0（dtype float32, C-order）。返回元数据。"""
    if not matrix:
        raise ValueError("空矩阵无法写出 .npy")
    width = len(matrix[0])
    if width == 0 or any(len(row) != width for row in matrix):
        raise ValueError("矩阵行列不一致或零维")
    header = "{'descr': '<f4', 'fortran_order': False, 'shape': (%d, %d), }" % (
        len(matrix), width)
    # header + newline 需 16 字节对齐
    pad = 16 - ((len(NPY_MAGIC) + 2 + 2 + len(header) + 1) % 16)
    header = header + " " * pad + "\n"
    hb = header.encode("latin1")
    with open(path, "wb") as f:
        f.write(NPY_MAGIC)
        f.write(bytes(NPY_VERSION))
        f.write(struct.pack("<H", len(hb)))
        f.write(hb)
        for row in matrix:
            f.write(_float32_bytes(row))
    return {"path": path, "shape": [len(matrix), width], "dtype": "float32"}


def write_csv(path: str, matrix: Sequence[Sequence[float]],
              chunk_ids: Optional[Sequence[str]] = None,
              uuids: Optional[Sequence[str]] = None) -> Dict[str, object]:
    """写 CSV：uuid/chunk_id + dim_0..dim_n（对齐课程 Listing 3 的 df_full）。"""
    if not matrix:
        raise ValueError("空矩阵无法写出 .csv")
    width = len(matrix[0])
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        head = []
        if uuids is not None:
            head.append("uuid")
        if chunk_ids is not None:
            head.append("chunk_id")
        head += ["dim_%d" % i for i in range(width)]
        w.writerow(head)
        for idx, row in enumerate(matrix):
            cells = []
            if uuids is not None:
                cells.append(uuids[idx] if idx < len(uuids) else "")
            if chunk_ids is not None:
                cells.append(chunk_ids[idx] if idx < len(chunk_ids) else "")
            cells += list(row)
            w.writerow(cells)
    return {"path": path, "rows": len(matrix), "cols": len(head)}


def try_write_parquet(path: str, matrix: Sequence[Sequence[float]],
                      chunk_ids: Optional[Sequence[str]] = None) -> Dict[str, object]:
    """尝试写真 parquet；pyarrow 不可用时返回 NOT_AVAILABLE（不伪造格式）。"""
    try:
        import pyarrow as pa  # type: ignore
        import pyarrow.parquet as pq  # type: ignore
    except ImportError:
        return {"path": path, "status": "NOT_AVAILABLE",
                "reason": "pyarrow 未安装（ADR-0003 零第三方依赖）；不伪造 parquet 格式"}
    try:
        cols = {"dim_%d" % i: [float(row[i]) for row in matrix]
                for i in range(len(matrix[0]))}
        if chunk_ids is not None:
            cols["chunk_id"] = list(chunk_ids)
        pq.write_table(pa.table(cols), path)
        return {"path": path, "status": "OK", "rows": len(matrix)}
    except Exception as exc:  # pragma: no cover - 依赖异常路径
        return {"path": path, "status": "ERROR", "reason": str(exc)}


def fetch_all_pages(fetch_page: Callable[[Optional[str]], Dict[str, object]],
                    page_size: int = 200) -> List[Dict[str, object]]:
    """游标分页拉取全部对象（模拟 GraphQL cursor-based pagination）。

    ``fetch_page(cursor)`` 返回 ``{"objects": [...], "next_cursor": str|None}``。
    """
    cursor: Optional[str] = None
    out: List[Dict[str, object]] = []
    seen = set()
    while True:
        page = fetch_page(cursor)
        objs = page.get("objects") or []
        for o in objs:
            out.append(o)
        nxt = page.get("next_cursor")
        # 有 next_cursor 就必须继续（末页可不足 page_size）；仅当无游标且本页为空时收尾
        if not nxt or nxt in seen:
            break
        seen.add(nxt)
        cursor = nxt
    return out


def export_vectors(out_dir: str,
                   matrix: Optional[Sequence[Sequence[float]]] = None,
                   chunk_ids: Optional[Sequence[str]] = None,
                   uuids: Optional[Sequence[str]] = None,
                   fetch_page: Optional[Callable[[Optional[str]], Dict[str, object]]] = None,
                   page_size: int = 200) -> Dict[str, object]:
    """S5 公开入口：把向量导出为三格式，返回结构化结果（含 parquet 状态）。"""
    if matrix is None:
        if fetch_page is None:
            raise ValueError("须提供 matrix 或 fetch_page")
        objects = fetch_all_pages(fetch_page, page_size)
        matrix = [o["vector"] for o in objects]  # type: ignore[index]
        chunk_ids = chunk_ids or [str(o.get("chunk_id", "")) for o in objects]
        uuids = uuids or [str(o.get("id", "")) for o in objects]
    if not matrix:
        raise ValueError("无向量可导出")
    os.makedirs(out_dir, exist_ok=True)
    npy = write_npy(os.path.join(out_dir, "embeddings.npy"), matrix)
    csv_res = write_csv(os.path.join(out_dir, "embeddings.csv"), matrix, chunk_ids, uuids)
    pq_res = try_write_parquet(os.path.join(out_dir, "embeddings.parquet"), matrix, chunk_ids)
    return {"step": "emb-c1", "count": len(matrix), "dim": len(matrix[0]),
            "npy": npy, "csv": csv_res, "parquet": pq_res,
            "all_formats_ok": pq_res.get("status") == "OK"}


def _main() -> int:
    """CLI 入口（SKILL.md emb-c1 证据命令）：无真实 store 时用内置夹具演示。"""
    import argparse
    from . import entry
    ap = argparse.ArgumentParser(description="emb-c1 向量导出")
    ap.add_argument("--store", default="", help="向量库端点（未接线时用夹具）")
    ap.add_argument("--out", default="./export", help="输出目录")
    ap.add_argument("--rows", default="", help="夹具向量 JSON 文件 {id: [vector]}")
    args = ap.parse_args()
    try:
        if args.rows:
            from . import entry as _e
            data = _e.load_json(args.rows)
            matrix = [list(v) for v in data.values()]
        else:
            from .harness import DeterministicEmbedder, fixture_corpus
            emb = DeterministicEmbedder()
            matrix = [emb.embed(t) for t in fixture_corpus().values()]
        res = export_vectors(args.out, matrix=matrix)
        res["mode"] = "fixture" if not args.rows else "corpus"
        res["store"] = args.store or "(fixture)"
        entry.emit(res)
        return 0
    except (ValueError, OSError) as exc:
        return entry.fail(str(exc))


if __name__ == "__main__":
    import sys
    sys.exit(_main())
