#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""术语一致性校验器（S1/S4）。

依据 GOVERNANCE.md §1.3 / §8.2 第 8 项：扫描 skills/**/*.md 与 docs/**/*.md
（排除 GLOSSARY.md 自身），检查是否使用了 GLOSSARY.md 中标注 `_Avoid_` 的废弃术语。
凡「自身即为规范词」的术语（如 OSAI、AI-300）不作为违规定义，避免误报。

退出码：0 = 通过；1 = 存在违规。
仅依赖 Python 标准库。
"""
import argparse
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_GLOSSARY = os.path.join(ROOT, "GLOSSARY.md")
DEFAULT_SCAN = [os.path.join(ROOT, "skills"), os.path.join(ROOT, "docs")]


def read(path):
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def display_path(path, base):
    """跨盘符安全地取相对路径；不同挂载点时回退为绝对路径。"""
    try:
        return os.path.relpath(path, base)
    except ValueError:
        return os.path.abspath(path)


def parse_glossary(path):
    """返回 (canonical_terms, avoid_terms)。"""
    text = read(path)
    canonical = set()
    avoid = []
    for line in text.splitlines():
        s = line.strip()
        m = re.match(r"^\*\*(.+?)\*\*:", s)
        if m:
            canonical.add(m.group(1).strip())
            continue
        if s.startswith("_Avoid_:"):
            raw = s.split(":", 1)[1]
            for t in re.split(r"[、,/]", raw):
                # 去除括号注释与反引号，仅保留实质词
                t = re.sub(r"[（(].*?[)）]", "", t).strip().strip("`").strip()
                if len(t) > 1:
                    avoid.append(t)
    # 规范词本身不作为违规定义
    avoid = [t for t in avoid if t not in canonical]
    return canonical, avoid


def iter_md(dirs, exclude):
    for base in dirs:
        if not os.path.isdir(base):
            continue
        for dp, _, fns in os.walk(base):
            for fn in fns:
                if fn.endswith(".md"):
                    p = os.path.abspath(os.path.join(dp, fn))
                    if p == os.path.abspath(exclude):
                        continue
                    yield p


def main(argv=None):
    ap = argparse.ArgumentParser(description="术语一致性校验器")
    ap.add_argument("--glossary", default=DEFAULT_GLOSSARY)
    ap.add_argument("--scan", action="append", default=None)
    args = ap.parse_args(argv)

    if not os.path.isfile(args.glossary):
        print("FAIL：未找到术语表 %s" % args.glossary)
        return 1

    canonical, avoid = parse_glossary(args.glossary)
    if not avoid:
        print("PASS：术语表无 _Avoid_ 废弃术语。")
        return 0

    scan_dirs = args.scan if args.scan else DEFAULT_SCAN
    errors = []
    for p in iter_md(scan_dirs, args.glossary):
        text = read(p)
        for t in avoid:
            if t in text:
                errors.append("%s: 使用了废弃术语 %r（见 GLOSSARY.md）" % (display_path(p, ROOT), t))

    if errors:
        print("ERROR (%d):" % len(errors))
        for e in errors:
            print("  - " + e)
        print("FAIL：术语一致性校验未通过。")
        return 1
    print("PASS：术语一致性校验通过（检查 %d 个废弃术语）。" % len(avoid))
    return 0


if __name__ == "__main__":
    sys.exit(main())
