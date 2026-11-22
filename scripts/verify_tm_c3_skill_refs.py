#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""SKILL.md Ch9 C3 段引用逐条字面核验（AC-11）。"""
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKILL = os.path.join(ROOT, "skills", "threat-model", "SKILL.md")
PATH_SYM_RE = re.compile(r"((?:tools|docs|scripts)/[A-Za-z0-9_./-]+\.(?:py|md))#([A-Za-z_][A-Za-z0-9_]*)")
PATH_ONLY_RE = re.compile(r"`((?:tools|docs|scripts)/[A-Za-z0-9_./-]+\.(?:py|md))`")
BARE_SYM_RE = re.compile(r"`(IdentityChainVerdict|iam_chain_graph|k8s_identity_chain|to_assets|to_boundaries|asset_ids_for|shortest_for_chain|to_verdict|claim_ids|compatible_with_iam_ctx)`")


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
    pkg = os.path.join(ROOT, "tools", "threat_model")
    all_src = "\n".join(open(os.path.join(pkg, f), encoding="utf-8").read()
                        for f in os.listdir(pkg) if f.endswith(".py"))
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
