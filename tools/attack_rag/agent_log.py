#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""agent.log 解析纯函数（Ch11 §11.5 日志回读闭环 · rag-10）。

零 PyRIT、零 I/O：输入为结构化事件/文本，输出为可机读判定。锚点见
docs/research/attack-rag-ch11-canonical.md（Ch11 extract L1295-1386）。
"""
import re
from collections import Counter
from typing import Dict, List, Optional

# 四类事件 + lm_error 单列（L1295-1316 / L1386）
KNOWN_EVENTS = ("ingest_ok", "lm_response", "lm_error", "heartbeat")
HEARTBEAT_SECONDS = 60  # L1316：heartbeat 每 60s 轮询

_OS_BUILD_RE = re.compile(r"^\d+\.\d+\.\d+\.\d+$")   # xx.x.xxxxx.xxxx (L287, 宽松位数)
_LLM_ADDR_RE = re.compile(r"^\d+\.\d+\.\d+\.\d+:\d+$")  # x.x.x.x:xxxx (L1388)


def classify_events(events: List[dict]) -> Dict[str, list]:
    """把 agent.log 事件按 event 字段分类；未知类型归 'other'（不臆造）。"""
    out = {name: [] for name in KNOWN_EVENTS}
    out["other"] = []
    for e in events:
        if not isinstance(e, dict):
            out["other"].append(e)
            continue
        kind = e.get("event")
        out[kind if kind in KNOWN_EVENTS else "other"].append(e)
    return out


def has_periodic_heartbeat(heartbeats: List[dict], period: int = HEARTBEAT_SECONDS) -> bool:
    """判定 heartbeat 是否含周期轮询（相邻 ts 差 == period 秒，允许 ≥2 条）。"""
    if len(heartbeats) < 2:
        return False
    from datetime import datetime
    stamps = []
    for h in heartbeats:
        try:
            stamps.append(datetime.fromisoformat(h.get("ts", "")))
        except (ValueError, TypeError):
            return False
    stamps.sort()
    return all((b - a).total_seconds() == period for a, b in zip(stamps, stamps[1:]))


def infer_trigger_keyword(responses: List[dict], min_repeat: int = 3) -> Optional[str]:
    """从 lm_response 的 query 中提取重复 ≥3 次的无意义串；无重复返回 None。"""
    queries = [r.get("query", "") for r in responses if isinstance(r, dict)]
    # 无意义串判据：长度 ≥ 12 且不含空格（L1314 的 oiajwdoiaj...）
    candidates = [q for q in queries if isinstance(q, str) and len(q) >= 12 and " " not in q]
    for word, count in Counter(candidates).most_common():
        if count >= min_repeat:
            return word
    return None


def infer_agent_identity(acl_rows: List[dict], hr_members=()) -> dict:
    """从 ACL 行推断 agent 运行身份：仅取 FullControl 主体（L1325-1338）。

    多个 FullControl 时按 HR 组成员过滤；仍不唯一返回歧义标记（不臆断）。
    """
    full = [r.get("identity", "") for r in acl_rows
            if isinstance(r, dict) and r.get("rights") == "FullControl"]
    hr = set(hr_members)
    filtered = [x for x in full if x in hr] if len(full) > 1 else full
    unique = sorted(set(filtered))
    if len(unique) == 1:
        return {"identity": unique[0], "ambiguous": False, "candidates": unique}
    return {"identity": "", "ambiguous": True, "candidates": unique}


def key_path_candidates(user: str) -> List[str]:
    """密钥路径候选顺序：id_ed25519 → id_rsa → id_ecdsa（L1342-1345）。"""
    return ["/home/%s/.ssh/id_ed25519" % user,
            "/home/%s/.ssh/id_rsa" % user,
            "/home/%s/.ssh/id_ecdsa" % user]


def extract_pem(text: str) -> str:
    """抽取 BEGIN/END 私钥块，保留换行；无私钥块返回空串（L1351-1386）。"""
    if not isinstance(text, str):
        return ""
    m = re.search(r"-----BEGIN [A-Z ]*PRIVATE KEY-----.*?-----END [A-Z ]*PRIVATE KEY-----",
                  text, re.DOTALL)
    return m.group(0) if m else ""


def check_quiz_format(value: str, kind: str) -> bool:
    """定格式问答校验：os_build (xx.x.xxxxx.xxxx) / llm_addr (x.x.x.x:xxxx)。"""
    if kind == "os_build":
        return bool(_OS_BUILD_RE.match(value or ""))
    if kind == "llm_addr":
        return bool(_LLM_ADDR_RE.match(value or ""))
    return False
