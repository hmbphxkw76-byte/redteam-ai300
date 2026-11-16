#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""契约消费者断言（S4）：登记表声明的依赖 ⊆ 契约清单。

背景：共享工具 `tools/collect_evidence.py` 的契约由 `docs/contracts/collect_evidence.contract.md`
唯一定义；每个消费者在 `docs/contracts/consumers.md` 声明其依赖的契约元素。
本脚本断言「每个消费者声明的每个契约元素都逐字出现在契约清单中」，用于拦截
「契约变更删除/改名某元素，但仍有消费者依赖旧元素」的跨技能契约漂移（S4）。

用法：
  python scripts/check_contract_consumers.py --check          # 断言依赖 ⊆ 清单（CI S1/S4）
  python scripts/check_contract_consumers.py --unmerged       # 列出状态=未合入 的消费者（S5）
退出码：0=通过；1=存在漂移/内部错误。
仅标准库。
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONTRACT = ROOT / "docs" / "contracts" / "collect_evidence.contract.md"
CONSUMERS = ROOT / "docs" / "contracts" / "consumers.md"


def _parse_consumers(text: str) -> list[dict[str, str]]:
    """解析 consumers.md 表格行，返回 [{skill, status, entry, deps}]。"""
    rows: list[dict[str, str]] = []
    for line in text.splitlines():
        s = line.strip()
        if not s.startswith("|"):
            continue
        cells = [c.strip() for c in s.strip("|").split("|")]
        if len(cells) < 4:
            continue
        if cells[0] in ("技能", "") or set(cells[0]) <= {"-", ":"}:
            continue  # 表头 / 分隔行
        rows.append({
            "skill": cells[0],
            "status": cells[1],
            "entry": cells[2],
            "deps": [d.strip() for d in cells[3].split(",") if d.strip()],
        })
    return rows


def check(root: Path = ROOT) -> tuple[bool, list[str]]:
    """返回 (是否通过, 漂移描述列表)。"""
    if not CONTRACT.is_file():
        return False, ["契约清单缺失：docs/contracts/collect_evidence.contract.md"]
    if not CONSUMERS.is_file():
        return False, ["消费者登记表缺失：docs/contracts/consumers.md"]
    manifest = CONTRACT.read_text(encoding="utf-8")
    problems: list[str] = []
    for c in _parse_consumers(CONSUMERS.read_text(encoding="utf-8")):
        for dep in c["deps"]:
            if dep not in manifest:
                problems.append(
                    "漂移：%s（%s）依赖的契约元素「%s」不在契约清单中（契约已删除/改名？）"
                    % (c["skill"], c["entry"], dep)
                )
    return (not problems), problems


def list_unmerged(root: Path = ROOT) -> list[dict[str, str]]:
    if not CONSUMERS.is_file():
        return []
    return [c for c in _parse_consumers(CONSUMERS.read_text(encoding="utf-8"))
            if c["status"] == "未合入"]


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="契约消费者断言（S4）")
    ap.add_argument("--check", action="store_true", help="断言消费者依赖 ⊆ 契约清单")
    ap.add_argument("--unmerged", action="store_true", help="列出未合入消费者（供契约 PR 点名）")
    args = ap.parse_args(argv)

    if args.unmerged:
        unmerged = list_unmerged()
        if not unmerged:
            print("未合入消费者：无。")
        for c in unmerged:
            print("未合入：%s（%s）" % (c["skill"], c["entry"]))
        return 0

    if not args.check:
        ap.print_help()
        return 2

    ok, problems = check()
    if not ok:
        print("契约消费者断言：BLOCKED（%d 项漂移）" % len(problems), file=sys.stderr)
        for p in problems:
            print("  - %s" % p, file=sys.stderr)
        return 1
    print("契约消费者断言：PASS（全部消费者依赖均在契约清单中）。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
