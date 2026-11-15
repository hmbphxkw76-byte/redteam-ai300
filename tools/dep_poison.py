#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""sc-05 依赖/包投毒 CLI（SKILL.md 命令入口）。

在镜像/包索引/requirements 注入恶意依赖（typosquat 或替换）；
输出 `InjectionConfig`（JSON），仅生成配置描述，不执行真实安装。
"""
import argparse
import dataclasses
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from tools.attack_supply_chain import inject_dependency  # noqa: E402


def main(argv=None):
    p = argparse.ArgumentParser(description="sc-05 依赖/包投毒")
    p.add_argument("--index", required=True, help="包索引/镜像源")
    p.add_argument("--pkg", required=True, help="被替换的合法包名")
    p.add_argument("--malicious", required=True, help="恶意包名（typosquat/替换）")
    args = p.parse_args(argv)
    cfg = inject_dependency(args.index, args.pkg, args.malicious)
    print(json.dumps(dataclasses.asdict(cfg), ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
