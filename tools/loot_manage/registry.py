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
DASH = "—"

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

    def to_text(self) -> str:
        lines = ["| " + " | ".join(self.header) + " |",
                 "|" + "|".join(["---"] * len(self.header)) + "|"]
        for r in self.rows:
            lines.append(format_row(r))
        lines += ["", ATTACK_PATH_HEADING, ""]
        for p in self.attack_paths:
            lines.append("- " + p)
        return "\n".join(lines) + "\n"


def parse_registry(text: str) -> Registry:
    """解析登记簿：首个 markdown 表 + `## 攻击路径` 小节。无表时返回空 Registry。"""
    header, rows, attack_paths = [], [], []
    table_started = False
    in_attack = False
    for raw in (text or "").splitlines():
        s = raw.strip()
        if s.startswith(ATTACK_PATH_HEADING):
            in_attack = True
            table_started = False
            continue
        if in_attack:
            if s.startswith("- "):
                attack_paths.append(s[2:].strip())
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
    return Registry(header, rows, attack_paths)


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

    # 空态
    if require_loot and not registry.rows:
        blocking.append("空态：登记簿无任何战利品（--require-loot）")

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
        "evidence": not miss_ev,
        "dual_channel": not dual_bad,
        "attack_path": attack_ok,
    }
    if check_pieces:
        checks["evidence_pieces"] = not bad_piece

    return {"passed": not blocking, "checks": checks, "blocking": blocking,
            "warnings": warnings, "flags": flags}


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
    if ATTACK_PATH_HEADING not in text:
        text = text.rstrip("\n") + "\n\n" + ATTACK_PATH_HEADING + "\n"
    lines = text.rstrip("\n").splitlines()
    while lines and not lines[-1].strip():
        lines.pop()
    lines.append("- " + line.strip())
    return "\n".join(lines) + "\n"
