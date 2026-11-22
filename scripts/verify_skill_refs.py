#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""SKILL.md 引用逐条核验（AC-11，收口要求）。

解析 `skills/foothold-traditional/SKILL.md` Ch9 段中反引号引用的
`tools/foothold_traditional/<module>.py#<symbol>` 与函数名，检查字面存在。
零外部依赖；返回非 0 表示有失效引用。
"""
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

SKILL = os.path.join(ROOT, "skills", "foothold-traditional", "SKILL.md")
PKG = os.path.join(ROOT, "tools", "foothold_traditional")
MODULE_RE = re.compile(r"tools/foothold_traditional/([a-z0-9_]+\.py)(?:#([A-Za-z_][A-Za-z0-9_]*))?")
PLAIN_SYMBOL_RE = re.compile(r"`(TriadVerdict|emit_strict_evidence|build_evidence_argv|run_ch9|ssrf_credential_entry|gpu_foothold_entry)`")


def main() -> int:
    if not os.path.isfile(SKILL):
        print("SKILL.md 不存在: %s" % SKILL)
        return 1
    text = open(SKILL, encoding="utf-8").read()
    section = text.split("## Ch9", 1)
    if len(section) < 2:
        print("SKILL.md 缺 Ch9 段")
        return 1
    ch9 = section[1].split("\n## ", 1)[0]
    problems = []
    for match in MODULE_RE.finditer(ch9):
        path = os.path.join(PKG, match.group(1))
        if not os.path.isfile(path):
            problems.append("模块不存在: %s" % match.group(1))
            continue
        symbol = match.group(2)
        if symbol:
            src = open(path, encoding="utf-8").read()
            if not re.search(r"^(def|class)\s+%s\b" % re.escape(symbol), src, re.M):
                problems.append("符号不存在: %s#%s" % (match.group(1), symbol))
    all_src = "".join(open(os.path.join(PKG, f), encoding="utf-8").read()
                      for f in os.listdir(PKG) if f.endswith(".py"))
    for match in PLAIN_SYMBOL_RE.finditer(ch9):
        if not re.search(r"^(def|class)\s+%s\b" % re.escape(match.group(1)), all_src, re.M):
            problems.append("符号不存在: %s" % match.group(1))
    if problems:
        for p in problems:
            print("FAIL: %s" % p)
        return 1
    print("PASS: SKILL.md Ch9 段全部引用字面完整")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
