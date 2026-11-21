#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""P0-1：读文件链（UID 解析 / 用户匹配 / 分批读取）——Ch5 §5.2 图21–22、C-14/C-15。

纯算法：解析 /proc/self/status 的 UID 行、在 /etc/passwd 文本中匹配用户，
按上下文预算把长文本分批（避免触发 vLLM 上下文上限中止，C-15）。
"""
import re
from typing import List, Optional

UNKNOWN = "不可判定"


def parse_uid(proc_status: str) -> Optional[int]:
    """从 /proc/self/status 文本解析真实 UID；无匹配返回 None。"""
    if not proc_status:
        return None
    match = re.search(r"^Uid:\s*(\d+)\s", str(proc_status), flags=re.MULTILINE)
    return int(match.group(1)) if match else None


def match_user(uid: Optional[int], passwd_text: str) -> str:
    """在 /etc/passwd 文本中按 UID 匹配用户名；无匹配记「不可判定」。"""
    if uid is None or not passwd_text:
        return UNKNOWN
    for line in str(passwd_text).splitlines():
        fields = line.split(":")
        if len(fields) >= 3 and fields[2].strip().isdigit() and int(fields[2]) == uid:
            return fields[0].strip()
    return UNKNOWN


def batch_lines(text: str, size: int) -> List[str]:
    """按行数分批；size<=0 抛错。批次按顺序可无损重组原文。"""
    if not isinstance(size, int) or size <= 0:
        raise ValueError("分批大小须为正整数")
    if text == "":
        return []
    lines = text.splitlines(keepends=True)
    if not lines:                      # 仅无换行符的空语义文本
        return [text]
    return ["".join(lines[i:i + size]) for i in range(0, len(lines), size)]
