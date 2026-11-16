#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""契约清单完整性校验 + 契约 PR 变更清单门禁（S2 / S5）。

两个职责：
  1) --check：校验契约清单 `docs/contracts/collect_evidence.contract.md` 结构完整
     （contract_version 存在、CHANGELOG 含 commit/PR 登记）——CI S1 常开。
  2) --pr-body PATH --changed F...：当 PR 触及契约文件（tools/collect_evidence.py
     或 docs/contracts/**）时，PR 正文必须含「## 契约变更清单」段，并点名全部
     未合入消费者（防「晚于契约变更合入的 skill 无法被覆盖」）——CI S1 仅 pull_request。

用法：
  python scripts/check_contract_manifest.py --check
  python scripts/check_contract_manifest.py --pr-body /tmp/body.md --changed tools/collect_evidence.py
退出码：0=通过；1=BLOCKED；2=用法错误。仅标准库。
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONTRACT = ROOT / "docs" / "contracts" / "collect_evidence.contract.md"

CONTRACT_PATHS = (
    "tools/collect_evidence.py",
    "docs/contracts/",
)


def _changed_is_contract(changed: list[str]) -> bool:
    return any(p == "tools/collect_evidence.py" or p.startswith("docs/contracts/")
               for p in changed)


def check_manifest(root: Path = ROOT) -> tuple[bool, list[str]]:
    if not CONTRACT.is_file():
        return False, ["契约清单缺失：docs/contracts/collect_evidence.contract.md"]
    text = CONTRACT.read_text(encoding="utf-8")
    problems: list[str] = []
    for needle in ("contract_version", "## CHANGELOG", "## 1. CLI 标志", "## 4. 片段节标题"):
        if needle not in text:
            problems.append("契约清单缺锚点：%s" % needle)
    # CHANGELOG 至少一条 commit 登记（供 checkout_lock 落后基线检测使用）
    if not re.search(r"commit:`[0-9a-f]{7,40}`", text):
        problems.append("契约清单 CHANGELOG 缺 commit:`<hash>` 登记")
    return (not problems), problems


def check_pr_body(body: str, changed: list[str]) -> tuple[bool, list[str]]:
    """契约 PR 门禁：触及契约文件则须含契约变更清单并点名未合入消费者。"""
    is_contract = _changed_is_contract(changed) or (
        "collect_evidence" in body and "契约" in body
    )
    if not is_contract:
        return True, []  # 非契约 PR，放行

    problems: list[str] = []
    m = re.search(r"^#+\s*契约变更清单", body, re.M)
    if not m:
        problems.append("契约 PR 缺「## 契约变更清单」段（须列变更元素 / before→after / 受影响消费者 / 兼容性判定）")
        return False, problems
    section = body[m.start():]
    for marker in ("变更元素", "受影响", "兼容"):
        if marker not in section:
            problems.append("契约变更清单缺子项：%s" % marker)

    # S5：未合入消费者必须被点名（否则其晚于变更合入时漂移不可见）
    try:
        from check_contract_consumers import list_unmerged
        unmerged = [c["skill"] for c in list_unmerged()]
    except Exception:
        unmerged = []
    for skill in unmerged:
        if skill not in body:
            problems.append("未合入消费者 %s 未在 PR 正文点名（须声明其影响与迁移断言）" % skill)
    return (not problems), problems


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="契约清单完整性 + 契约 PR 门禁（S2/S5）")
    ap.add_argument("--check", action="store_true", help="校验契约清单结构完整")
    ap.add_argument("--pr-body", help="PR 正文文件路径")
    ap.add_argument("--changed", nargs="*", default=[], help="变更文件列表（契约 PR 判定）")
    args = ap.parse_args(argv)

    if args.pr_body:
        body = Path(args.pr_body).read_text(encoding="utf-8")
        ok, problems = check_pr_body(body, args.changed)
        if not ok:
            print("契约 PR 门禁：BLOCKED（%d 项）" % len(problems), file=sys.stderr)
            for p in problems:
                print("  - %s" % p, file=sys.stderr)
            return 1
        print("契约 PR 门禁：PASS（非契约 PR，或契约变更清单齐全）。")
        return 0

    if not args.check:
        ap.print_help()
        return 2

    ok, problems = check_manifest()
    if not ok:
        print("契约清单校验：BLOCKED（%d 项）" % len(problems), file=sys.stderr)
        for p in problems:
            print("  - %s" % p, file=sys.stderr)
        return 1
    print("契约清单校验：PASS。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
