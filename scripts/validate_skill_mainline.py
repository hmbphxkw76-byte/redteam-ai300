#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""独立只读校验：技能主线留痕与孤儿规格发现（AC-11）。

不修改任何文件，不接入 CI 并发长行；默认退出 0 仅报告，--strict 时存在缺口退出 1。
判据：AGENTS.md C1/C8 + docs/operations/skill-mainline-workflow.md:3,109-123。
"""
from __future__ import annotations

import argparse
import glob
import os
import sys
from typing import Any

MAINLINE_TOKEN = "skill-mainline-workflow"


def scan(root: str) -> dict[str, Any]:
    skills = []
    for path in sorted(glob.glob(os.path.join(root, "skills", "*", "SKILL.md"))):
        name = os.path.basename(os.path.dirname(path))
        with open(path, encoding="utf-8") as f:
            text = f.read()
        spec_v1 = os.path.join(root, "docs", "specs", name + "-spec-v1.md")
        spec_v2 = os.path.join(root, "docs", "specs", name + "-spec-v2.md")
        gates = glob.glob(os.path.join(root, "docs", "operations", name + "-gate-stage*.md"))
        gaps = []
        if MAINLINE_TOKEN not in text:
            gaps.append("SKILL.md 未引用主线唯一可信源")
        if not os.path.isfile(spec_v1):
            gaps.append("缺 docs/specs 规格 v1")
        if not os.path.isfile(spec_v2):
            gaps.append("缺 docs/specs 规格 v2")
        if len(gates) < 10:
            gaps.append("阶段门禁记录 %d/10" % len(gates))
        skills.append({"skill": name, "ok": not gaps, "gaps": gaps})

    root_specs = sorted(
        os.path.basename(p) for p in
        glob.glob(os.path.join(root, "spec-*.md"))
    )
    return {"skills": skills, "root_specs": root_specs,
            "ok": all(s["ok"] for s in skills) and not root_specs}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="技能主线留痕与孤儿规格只读校验")
    ap.add_argument("--root", default=os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    ap.add_argument("--strict", action="store_true", help="存在缺口时退出 1")
    args = ap.parse_args(list(argv) if argv is not None else None)
    data = scan(args.root)
    for s in data["skills"]:
        print("%-24s %s" % (s["skill"], "PASS" if s["ok"] else "GAP: " + "；".join(s["gaps"])))
    print("根层影子规格：%d 份" % len(data["root_specs"]))
    for name in data["root_specs"]:
        print("  - %s" % name)
    print("总计：%s" % ("PASS" if data["ok"] else "BLOCKED"))
    if args.strict and not data["ok"]:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
