#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""sc-06 构建/运行时触发 CLI（SKILL.md 命令入口）。

使投毒在构建或推理时执行非预期代码；输出 `InjectionConfig`（JSON），
仅生成配置描述，不执行 payload。
"""
import argparse
import dataclasses
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from tools.attack_supply_chain import inject_build  # noqa: E402


def main(argv=None):
    p = argparse.ArgumentParser(description="sc-06 构建/运行时触发")
    p.add_argument("--build", required=True, help="CI/构建系统标识")
    p.add_argument("--payload", required=True, help="构建期执行的载荷描述")
    args = p.parse_args(argv)
    cfg = inject_build(args.build, args.payload)
    print(json.dumps(dataclasses.asdict(cfg), ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
