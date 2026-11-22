#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""SKILL.md Ch9 B6 段引用逐条字面核验（AC-10）。

检查反引号中的 `tools/.../<module>.py#<symbol>` 与路径指针是否存在于工作树。
不解析正文语义，只查字面（C8 收口要求）。
"""
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKILL = os.path.join(ROOT, "skills", "attack-supply-chain", "SKILL.md")
PATH_SYM_RE = re.compile(r"((?:tools|docs|scripts)/[A-Za-z0-9_./-]+\.(?:py|md))#([A-Za-z_][A-Za-z0-9_]*)")
PATH_ONLY_RE = re.compile(r"`((?:tools|docs|scripts)/[A-Za-z0-9_./-]+\.(?:py|md))`")
BARE_SYM_RE = re.compile(r"`(BoundaryVerdict|classify|build_evidence_argv|emit_strict_evidence|run_boundary)`")


def main() -> int:
    if not os.path.isfile(SKILL):
        print("SKILL.md 不存在: %s" % SKILL)
        return 1
    text = open(SKILL, encoding="utf-8").read()
    parts = text.split("## Ch9", 1)
    if len(parts) < 2:
        print("SKILL.md 缺 Ch9 段")
        return 1
    section = parts[1].split("\n## ", 1)[0]
    problems = []
    for m in PATH_SYM_RE.finditer(section):
        rel, sym = m.group(1), m.group(2)
        path = os.path.join(ROOT, rel)
        if not os.path.isfile(path):
            problems.append("路径不存在: %s" % rel)
            continue
        src = open(path, encoding="utf-8").read()
        if not re.search(r"^(def|class)\s+%s\b" % re.escape(sym), src, re.M):
            problems.append("符号不存在: %s#%s" % (rel, sym))
    for m in PATH_ONLY_RE.finditer(section):
        if not os.path.isfile(os.path.join(ROOT, m.group(1))):
            problems.append("路径不存在: %s" % m.group(1))
    srcs = []
    for d in (os.path.join(ROOT, "tools", "attack_supply_chain"),):
        for f in os.listdir(d):
            if f.endswith(".py"):
                srcs.append(open(os.path.join(d, f), encoding="utf-8").read())
    all_src = "\n".join(srcs)
    for m in BARE_SYM_RE.finditer(section):
        if not re.search(r"^(def|class)\s+%s\b" % re.escape(m.group(1)), all_src, re.M):
            problems.append("符号不存在: %s" % m.group(1))
    if problems:
        for p in problems:
            print("FAIL: %s" % p)
        return 1
    print("PASS: SKILL.md Ch9 段全部引用字面完整")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
