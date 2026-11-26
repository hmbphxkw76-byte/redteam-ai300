#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""策略库读取与聚合（方案 P5）。

策略是**数据**不是代码：新增打法只改 `data/strategies.json`，不改本模块。
聚合只报「尝试数 / 生效数 / 成功率」，且生效判定一律经 `dialogue.score`
（确定性 → 否定语境 → 语义否决），不接受调用方自带判据，避免口径漂移。
"""
import json
import os
from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

DEFAULT_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "data", "strategies.json")


@dataclass(frozen=True)
class Strategy:
    """一条可执行策略。`steps` 顺序发送，判定取最后一条响应。"""

    id: str
    name: str
    rationale: str
    status: str                       # proven | unstable | refuted | unproven
    steps: Tuple[str, ...]
    pattern: str
    require_affirmative: bool = False
    target_shape: Tuple[str, ...] = ()
    observed: Mapping[str, str] = field(default_factory=dict)

    def as_dict(self) -> Dict[str, object]:
        return {
            "id": self.id, "name": self.name, "status": self.status,
            "rationale": self.rationale, "steps": list(self.steps),
            "pattern": self.pattern,
            "require_affirmative": self.require_affirmative,
            "target_shape": list(self.target_shape),
            "observed": dict(self.observed),
        }


def _parse(raw: Mapping[str, object]) -> Strategy:
    scorer = raw.get("scorer") or {}
    if not isinstance(scorer, Mapping) or not scorer.get("pattern"):
        raise ValueError("策略 %s 缺 scorer.pattern" % raw.get("id"))
    steps = raw.get("steps") or ()
    if isinstance(steps, str):
        steps = (steps,)
    return Strategy(
        id=str(raw["id"]),
        name=str(raw.get("name") or raw["id"]),
        rationale=str(raw.get("rationale") or ""),
        status=str(raw.get("status") or "unproven"),
        steps=tuple(str(s) for s in steps),
        pattern=str(scorer["pattern"]),
        require_affirmative=bool(scorer.get("require_affirmative")),
        target_shape=tuple(raw.get("target_shape") or ()),
        observed=dict(raw.get("observed") or {}),
    )


def load(path: Optional[str] = None) -> List[Strategy]:
    """读取策略库；文件缺失返回空列表（不臆造默认策略）。"""
    target = path or DEFAULT_PATH
    if not os.path.exists(target):
        return []
    with open(target, encoding="utf-8") as handle:
        data = json.load(handle)
    rows = data.get("strategies") if isinstance(data, dict) else data
    return [_parse(row) for row in (rows or [])]


def select(strategies: Iterable[Strategy], ids: Sequence[str] = (),
           status: str = "") -> List[Strategy]:
    """按 ID 或状态筛选；两者皆空时返回全部。"""
    pool = list(strategies)
    if ids:
        wanted = {s.strip().upper() for s in ids if s.strip()}
        pool = [s for s in pool if s.id.upper() in wanted]
    if status:
        pool = [s for s in pool if s.status == status]
    return pool


def aggregate(runs: Iterable[Mapping[str, object]]) -> Dict[str, Dict[str, object]]:
    """按策略聚合尝试数与生效数。

    `runs` 每项需含 `strategy_id` 与 `effective`（布尔）；不在此重算判定，
    避免出现「聚合口径 ≠ 评分链口径」的第二套判据。
    """
    out: Dict[str, Dict[str, object]] = {}
    for run in runs:
        sid = str(run.get("strategy_id") or "")
        if not sid:
            continue
        row = out.setdefault(sid, {"attempts": 0, "effective": 0, "rate": 0.0})
        row["attempts"] = int(row["attempts"]) + 1
        if run.get("effective"):
            row["effective"] = int(row["effective"]) + 1
    for row in out.values():
        attempts = int(row["attempts"])
        row["rate"] = round(int(row["effective"]) / attempts, 3) if attempts else 0.0
    return out


def render_table(strategies: Sequence[Strategy]) -> str:
    """输出人读的策略表（供 --list-strategies）。"""
    head = "%-16s %-14s %-9s %-8s %s" % ("ID", "名称", "状态", "实测", "载荷要点")
    lines = [head, "-" * len(head)]
    for item in strategies:
        observed = item.observed.get("result", "-")
        lines.append("%-16s %-14s %-9s %-8s %s" % (
            item.id, item.name[:14], item.status, observed,
            (item.steps[0] if item.steps else "")[:40]))
    return "\n".join(lines)


__all__: Sequence[str] = (
    "DEFAULT_PATH", "Strategy", "load", "select", "aggregate", "render_table",
)
