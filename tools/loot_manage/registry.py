#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""loot-manage 登记簿核心：解析 / 校验 / 追加（纯标准库）。

行为唯一来源：`skills/loot-manage/SKILL.md`；事实源：`docs/research/loot-manage-canonical.md`。
对外契约见 `validate()` 返回 dict；CLI 薄封装见 `cli.py`。本模块不含 argparse、不读网络。
"""
from __future__ import annotations

import os
import re
from dataclasses import dataclass, field

# 固定 8 列（SKILL.md「执行体」）。表头按列名集合匹配，列序可变（AC-12）。
COLUMNS = ["编号", "类型", "内容", "来源主机", "证据片段路径", "时间戳", "状态", "双通道"]
TYPES = {"凭据", "会话", "flag"}
STATUSES_BY_TYPE = {
    "凭据": {"有效", "失效"},
    "会话": {"存活", "失效"},
    "flag": {"已取证", "失效"},
}
DEFAULT_STATUS = {"凭据": "有效", "会话": "存活", "flag": "已取证"}
ATTACK_PATH_HEADING = "## 攻击路径"
EMPTY_STATE_HEADING = "## 空态"
DASH = "—"
# 小节标题容错：SKILL.md「loot-04」模板写作 `### 攻击路径`，本工具自生成用 `##`；
# 两种层级都须识别，否则照模板手写的登记簿会漏解析该小节。
_ATTACK_HEADING_RE = re.compile(r"^#{1,6}\s*攻击路径\s*$")
_EMPTY_HEADING_RE = re.compile(r"^#{1,6}\s*空态\s*$")
_ANY_HEADING_RE = re.compile(r"^#{1,6}\s")
_REASON_RE = re.compile(r"^[-*]\s*原因\s*[：:]\s*(.*)$")

SKELETON = """# 战利品登记簿 (loot registry)

> 单一事实源（GOVERNANCE §5.2）。每行一条战利品；「证据片段路径」指向 `collect_evidence.py` 产物，不重复存证据本体。

| 编号 | 类型 | 内容 | 来源主机 | 证据片段路径 | 时间戳 | 状态 | 双通道 |
|---|---|---|---|---|---|---|---|

## 攻击路径

<!-- 每完成一段攻击路径追加一行：- 入口 A → B（trad-04 flag）→ C（trad-07 flag） -->
"""


def normalize_col(name: str) -> str:
    """列名归一：去掉括号补充说明，如「双通道（面板值 + 截图路径）」→「双通道」。"""
    return re.split(r"[（(]", (name or "").strip())[0].strip()


def _split_row(line: str):
    s = line.strip()
    if s.startswith("|"):
        s = s[1:]
    if s.endswith("|"):
        s = s[:-1]
    return [c.strip() for c in s.split("|")]


def _is_separator(cells) -> bool:
    return bool(cells) and all(re.fullmatch(r":?-{2,}:?", c) for c in cells if c != "")


@dataclass
class LootRow:
    id: str = ""
    type: str = ""
    content: str = ""
    host: str = ""
    evidence: str = ""
    timestamp: str = ""
    status: str = ""
    dual: str = ""
    raw: list = field(default_factory=list)

    @classmethod
    def from_cells(cls, cells):
        padded = list(cells) + [""] * (8 - len(cells))
        return cls(padded[0], padded[1], padded[2], padded[3], padded[4],
                   padded[5], padded[6], padded[7], list(cells))

    def to_cells(self):
        return [self.id, self.type, self.content, self.host,
                self.evidence, self.timestamp, self.status, self.dual]


@dataclass
class Registry:
    header: list = field(default_factory=list)
    rows: list = field(default_factory=list)
    attack_paths: list = field(default_factory=list)
    # 空态记录（SKILL.md「失败与豁免」）：{"reason": str, "lines": [str]}
    empty_state: dict | None = None

    def to_text(self) -> str:
        lines = ["| " + " | ".join(self.header) + " |",
                 "|" + "|".join(["---"] * len(self.header)) + "|"]
        for r in self.rows:
            lines.append(format_row(r))
        lines += ["", ATTACK_PATH_HEADING, ""]
        for p in self.attack_paths:
            lines.append("- " + p)
        if self.empty_state and self.empty_state.get("reason"):
            lines += ["", EMPTY_STATE_HEADING, "",
                      "- 原因：%s" % self.empty_state["reason"]]
        return "\n".join(lines) + "\n"


def parse_registry(text: str) -> Registry:
    """解析登记簿：首个 markdown 表 + 「攻击路径」小节 + 「空态」小节。

    「攻击路径」标题接受 `##` 与 `###`（SKILL.md 模板层级不同）。无表时返回空 Registry。
    """
    header, rows, attack_paths = [], [], []
    table_started = False
    in_attack = in_empty = False
    empty_lines = []
    for raw in (text or "").splitlines():
        s = raw.strip()
        if _ATTACK_HEADING_RE.match(s):
            in_attack, in_empty, table_started = True, False, False
            continue
        if _EMPTY_HEADING_RE.match(s):
            in_empty, in_attack, table_started = True, False, False
            continue
        if _ANY_HEADING_RE.match(s):
            in_attack = in_empty = False
            continue
        if in_attack:
            if s.startswith("- "):
                attack_paths.append(s[2:].strip())
            continue
        if in_empty:
            if s:
                empty_lines.append(s)
            continue
        if s.startswith("|"):
            cells = _split_row(s)
            if not table_started:
                header = cells
                table_started = True
            elif _is_separator(cells):
                continue
            else:
                rows.append(LootRow.from_cells(cells))

    empty_state = None
    if empty_lines:
        reason = ""
        for ln in empty_lines:
            m = _REASON_RE.match(ln)
            if m:
                reason = m.group(1).strip()
        empty_state = {"reason": reason, "lines": empty_lines}
    return Registry(header, rows, attack_paths, empty_state)


def parse_dual(cell: str):
    """解析双通道单元格：面板=<值>；截图=<路径>。返回 (panel, shot)。

    注意：本登记的「截图=」是截图**路径**，非 flag 值；值级一致性由 verify-evidence
    在下游读取截图核对，本工具只校验两通道均已提供（== consistent）。
    """
    panel = shot = ""
    for part in re.split(r"[；;]", cell or ""):
        p = part.strip()
        if p.startswith("面板="):
            panel = p[len("面板="):].strip()
        elif p.startswith("截图="):
            shot = p[len("截图="):].strip()
    return panel, shot


def _resolve(root: str, path: str) -> str:
    return path if os.path.isabs(path) else os.path.join(root, path)


def fragment_pieces(text: str):
    """判定 collect_evidence 证据片段三件套是否齐全。"""
    def section(title):
        m = re.search(r"####\s*" + re.escape(title) + r".*?(?=\n####\s|\Z)",
                      text or "", re.S)
        return m.group(0) if m else ""

    cmd = section("确切命令")
    out = section("关键输出")
    shot = section("截图")
    has_cmd = bool(cmd) and "（未提供）" not in cmd
    has_out = bool(out) and "（未提供）" not in out
    has_shot = bool(shot) and ("![" in shot or "截图捕获钩子" in shot)
    return {"command": has_cmd, "output": has_out, "screenshot": has_shot,
            "complete": has_cmd and has_out and has_shot}


def validate(registry: Registry, root: str = ".", require_loot: bool = False,
             check_pieces: bool = False) -> dict:
    """执行质量门校验，返回 {passed, checks, blocking, warnings, flags}。

    flags 输出即 verify-evidence 的消费契约（AC-6）。
    """
    blocking, warnings = [], []

    # 表头列（按列名集合，非索引位置）
    norm = [normalize_col(c) for c in registry.header]
    checks_cols = len(norm) == 8 and set(norm) == set(COLUMNS)
    if not checks_cols:
        blocking.append("表头列不符：期望 8 列 %s，实际 %s" % (COLUMNS, registry.header))

    # 行单元格数
    bad_rows = [r.id or "(行)" for r in registry.rows if len(r.raw) != 8]
    if bad_rows:
        blocking.append("以下行单元格数≠8：%s" % "、".join(bad_rows))

    # 类型 / 状态
    type_bad, status_bad = [], []
    for r in registry.rows:
        if r.type not in TYPES:
            type_bad.append("%s:%s" % (r.id, r.type))
        elif r.status not in STATUSES_BY_TYPE[r.type]:
            status_bad.append("%s:%s" % (r.id, r.status))
    if type_bad:
        blocking.append("类型非法：%s" % "、".join(type_bad))
    if status_bad:
        blocking.append("状态与类型不符：%s" % "、".join(status_bad))

    # 编号
    ids = [r.id for r in registry.rows]
    id_bad = [i for i in ids if not re.fullmatch(r"L-\d+", i or "")]
    dup = sorted({i for i in ids if ids.count(i) > 1})
    if id_bad:
        blocking.append("编号格式非法（应为 L-<n>）：%s" % "、".join(id_bad))
    if dup:
        blocking.append("编号重复：%s" % "、".join(dup))

    # 来源主机（质量门「可追溯」：主机为空或占位即不可追溯）
    host_bad = [r.id for r in registry.rows if not r.host or r.host == DASH]
    if host_bad:
        blocking.append("来源主机为空：%s" % "、".join(host_bad))

    # 证据片段路径存在
    miss_ev = [r.id for r in registry.rows
               if r.evidence and r.evidence != DASH
               and not os.path.isfile(_resolve(root, r.evidence))]
    if miss_ev:
        blocking.append("证据片段路径不存在：%s" % "、".join(miss_ev))

    # 三件套（可选，--check-pieces）
    if check_pieces:
        bad_piece = []
        for r in registry.rows:
            if not r.evidence or r.evidence == DASH:
                continue
            p = _resolve(root, r.evidence)
            if os.path.isfile(p):
                with open(p, encoding="utf-8", errors="replace") as f:
                    if not fragment_pieces(f.read())["complete"]:
                        bad_piece.append(r.id)
        if bad_piece:
            blocking.append("证据片段三件套不全：%s" % "、".join(bad_piece))

    # flag 双通道
    flags, dual_bad = [], []
    for r in registry.rows:
        if r.type == "flag":
            panel, shot = parse_dual(r.dual)
            present = bool(panel) and bool(shot)
            if not present:
                dual_bad.append(r.id)
            flags.append({"id": r.id, "host": r.host, "panel": panel,
                          "shot": shot, "consistent": present})
    if dual_bad:
        blocking.append("flag 行缺双通道（面板=/截图=）：%s" % "、".join(dual_bad))

    # 攻击路径（有登记行时须非空）
    attack_ok = bool(registry.attack_paths) if registry.rows else True
    if registry.rows and not registry.attack_paths:
        blocking.append("有登记行但「攻击路径」小节为空")

    # 空态（SKILL「失败与豁免」）：记录原因即有效产出；--require-loot 仍作缺口信号
    empty_state = registry.empty_state or None
    if require_loot and not registry.rows:
        msg = "空态：登记簿无任何战利品（--require-loot）"
        if empty_state and empty_state.get("reason"):
            msg += "；已记录原因：%s" % empty_state["reason"]
        blocking.append(msg)

    # proof.txt 软校验（warning，不阻断；G2）
    proof_rows = [r.id for r in registry.rows if "proof.txt" in (r.content + r.evidence)]
    if len(proof_rows) > 1:
        warnings.append("proof.txt 多次登记（%s），域控 flag 仅可提交一次" % "、".join(proof_rows))
    for r in registry.rows:
        if "proof.txt" in (r.content + r.evidence) and "仅可提交一次" not in r.dual:
            warnings.append("%s：proof.txt 行未标注「仅可提交一次」" % r.id)

    checks = {
        "columns": checks_cols,
        "rows": not bad_rows,
        "types": not type_bad,
        "statuses": not status_bad,
        "ids": not id_bad and not dup,
        "hosts": not host_bad,
        "evidence": not miss_ev,
        "dual_channel": not dual_bad,
        "attack_path": attack_ok,
    }
    if check_pieces:
        checks["evidence_pieces"] = not bad_piece

    return {"passed": not blocking, "checks": checks, "blocking": blocking,
            "warnings": warnings, "flags": flags, "empty_state": empty_state}


def format_row(row: LootRow) -> str:
    return "| " + " | ".join(row.to_cells()) + " |"


def append_row(text: str, row: LootRow) -> str:
    """在表格末尾插入一行；若无表格则先落骨架再插入。"""
    if not parse_registry(text).header:
        text = (text.rstrip("\n") + "\n\n" + SKELETON) if text.strip() else SKELETON
    lines = text.splitlines()
    last = None
    for i, ln in enumerate(lines):
        if ln.strip().startswith("|"):
            last = i
    if last is None:
        return text.rstrip("\n") + "\n" + format_row(row) + "\n"
    lines.insert(last + 1, format_row(row))
    return "\n".join(lines) + "\n"


def append_attack_path(text: str, line: str) -> str:
    """在「攻击路径」小节末尾追加一行（该小节后若还有其它小节，不会写错位置）。"""
    text = text or ""
    lines = text.rstrip("\n").splitlines()
    idx = next((i for i, ln in enumerate(lines) if _ATTACK_HEADING_RE.match(ln.strip())), None)
    if idx is None:
        lines += ["", ATTACK_PATH_HEADING]
        idx = len(lines) - 1
    end = len(lines)
    for j in range(idx + 1, len(lines)):
        if _ANY_HEADING_RE.match(lines[j].strip()):
            end = j
            break
    insert_at = idx + 1
    for j in range(idx + 1, end):
        if lines[j].strip():
            insert_at = j + 1
    lines.insert(insert_at, "- " + line.strip())
    return "\n".join(lines) + "\n"


def query_rows(registry: Registry, type_=None, status=None, host=None) -> list:
    """按类型 / 状态 / 主机筛选登记行（SKILL loot-02.3：横向前查询复用）。"""
    out = []
    for r in registry.rows:
        if type_ and r.type != type_:
            continue
        if status and r.status != status:
            continue
        if host and r.host != host:
            continue
        out.append(r)
    return out


def reusable_rows(registry: Registry) -> list:
    """横向复用候选：凭据=有效、会话=存活；失效项不得复用。"""
    return [r for r in registry.rows if r.status in ("有效", "存活")]


def update_status(text: str, row_id: str, status: str):
    """原位更新登记行状态，保留行序与其余单元格（SKILL「失败与豁免」）。

    返回 (new_text, ok, message)；未找到行或状态与类型不匹配时原文本不变。
    """
    lines = (text or "").splitlines()
    header_idx = None
    for i, ln in enumerate(lines):
        # 表头是首个以 `|` 开头的行；标题/引用块在前，不能因其提前中止。
        if ln.strip().startswith("|"):
            header_idx = i
            break
    if header_idx is None:
        return text, False, "登记簿中未找到表格"
    header = [normalize_col(c) for c in _split_row(lines[header_idx])]
    if "状态" not in header or "编号" not in header:
        return text, False, "表头缺少「编号」或「状态」列"
    st_idx, id_idx = header.index("状态"), header.index("编号")
    type_idx = header.index("类型") if "类型" in header else None
    for i in range(header_idx + 1, len(lines)):
        s = lines[i].strip()
        if not s.startswith("|"):
            break
        cells = _split_row(s)
        if _is_separator(cells):
            continue
        if len(cells) <= max(st_idx, id_idx):
            continue
        if cells[id_idx] != row_id:
            continue
        rtype = cells[type_idx] if type_idx is not None and type_idx < len(cells) else ""
        allowed = STATUSES_BY_TYPE.get(rtype)
        if allowed and status not in allowed:
            return text, False, "状态「%s」不适用于类型「%s」（允许：%s）" % (
                status, rtype, "、".join(sorted(allowed)))
        cells[st_idx] = status
        lines[i] = "| " + " | ".join(cells) + " |"
        return "\n".join(lines) + "\n", True, "%s 状态更新为「%s」" % (row_id, status)
    return text, False, "未找到编号「%s」的登记行" % row_id


def mark_empty_state(text: str, reason: str) -> str:
    """写入或更新「空态」小节的原因（SKILL「失败与豁免」：空态本身即有效产出）。"""
    reason = (reason or "").strip()
    lines = (text or "").splitlines()
    idx = next((i for i, ln in enumerate(lines) if _EMPTY_HEADING_RE.match(ln.strip())), None)
    if idx is None:
        lines += ["", EMPTY_STATE_HEADING, "", "- 原因：%s" % reason]
        return "\n".join(lines) + "\n"
    end = len(lines)
    for j in range(idx + 1, len(lines)):
        if _ANY_HEADING_RE.match(lines[j].strip()):
            end = j
            break
    for j in range(idx + 1, end):
        if _REASON_RE.match(lines[j].strip()):
            lines[j] = "- 原因：%s" % reason
            return "\n".join(lines) + "\n"
    lines.insert(idx + 1, "- 原因：%s" % reason)
    return "\n".join(lines) + "\n"
