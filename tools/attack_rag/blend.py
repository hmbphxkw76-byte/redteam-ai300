#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""P1-5：文档融合安全区计算 + citation 命名对齐（Ch5 §5.3 图30–34、C-22..C-24）。

C-23：800 字符块 / 200 重叠，预览可达 500 → 从偏移 501 起放 100 字符，
载荷不得进入下一块预览（总量 ≤600）；C-24：从检索回执推断命名风格。
纯函数，无 IO。
"""
UNKNOWN = "不可判定"
DEFAULT_PREVIEW = 500


def safe_offset(chunk_size: int, overlap: int, preview_size: int = DEFAULT_PREVIEW) -> int:
    """返回载荷起始偏移；超出安全区抛 ValueError（C-23）。"""
    if chunk_size <= 0 or overlap < 0 or preview_size < 0:
        raise ValueError("块大小须为正、重叠与预览大小须非负")
    if overlap >= chunk_size:
        raise ValueError("重叠须小于块大小")
    ceiling = chunk_size - overlap           # 载荷结束不得超过此值
    start = preview_size + 1                 # 从预览窗口之后 1 字符起
    if start >= ceiling:
        raise ValueError("预览窗口过大，无安全区（预览 %d ≥ 上限 %d）"
                         % (preview_size, ceiling))
    return start


def payload_budget(chunk_size: int, overlap: int) -> int:
    """载荷可用字符预算：块尾到下一块预览起点之前（C-23 的 ≤600）。"""
    if chunk_size <= 0 or overlap < 0 or overlap >= chunk_size:
        raise ValueError("非法的块大小/重叠")
    return chunk_size - overlap


def citation_name(style: str = "", topic: str = "") -> str:
    """按检索回执推断文件名（如 MC1_ 前缀 + .pdf）；无回执记「不可判定」。"""
    prefix = (style or "").strip()
    subject = (topic or "").strip()
    if not prefix:
        return UNKNOWN
    if not subject:
        subject = "Document"
    return "%s%s.pdf" % (prefix, subject.replace(" ", "_"))
