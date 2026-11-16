#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""S1 编译门禁：按 scripts/tools_manifest.json 显式清单编译 tools/ 与 scripts/。

替换 ci.yml 原先散落的 py_compile glob 长行。清单是编译范围的唯一来源；
新增包/脚本须先登记清单，否则不进门禁（可在 --check-missing 模式下发现）。

用法：
  python scripts/check_tools_compile.py            # 编译清单内全部 .py
  python scripts/check_tools_compile.py --check-missing  # 另报告未登记的 .py（不失败）
退出码：0=全部编译通过；1=存在编译错误；2=用法/清单错误。
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import py_compile
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MANIFEST = os.path.join(ROOT, "scripts", "tools_manifest.json")


def load_manifest():
    with open(MANIFEST, encoding="utf-8") as handle:
        return json.load(handle)


def main(argv=None):
    ap = argparse.ArgumentParser(description="按显式清单编译 tools/ 与 scripts/")
    ap.add_argument("--check-missing", action="store_true",
                    help="报告磁盘上存在但未登记入清单的 .py（仅报告，不失败）")
    args = ap.parse_args(argv)
    manifest = load_manifest()
    compile_cfg = manifest["compile"]

    files = []
    for pkg in compile_cfg["packages"]:
        files.extend(sorted(glob.glob(os.path.join(ROOT, pkg, "*.py"))))
    for rel in compile_cfg["scripts"] + compile_cfg["helper_scripts"]:
        files.append(os.path.join(ROOT, rel))

    errors = []
    for path in files:
        try:
            py_compile.compile(path, doraise=True)
        except (py_compile.PyCompileError, OSError) as exc:
            errors.append("%s: %s" % (os.path.relpath(path, ROOT), exc))

    if args.check_missing:
        registered = set(os.path.normcase(os.path.abspath(p)) for p in files)
        on_disk = set(os.path.normcase(p) for p in
                      glob.glob(os.path.join(ROOT, "tools", "*.py")) +
                      glob.glob(os.path.join(ROOT, "tools", "*", "*.py")) +
                      glob.glob(os.path.join(ROOT, "scripts", "*.py")))
        missing = sorted(os.path.relpath(p, ROOT) for p in on_disk - registered)
        if missing:
            print("未登记 .py（%d）：" % len(missing))
            for m in missing:
                print("  - " + m)

    print("编译检查：%d 个文件，失败 %d" % (len(files), len(errors)))
    for err in errors:
        print("  - " + err, file=sys.stderr)
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
