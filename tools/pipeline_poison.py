#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""sc-04 数据管道投毒 CLI（SKILL.md 命令入口）。

在 ETL / 预处理阶段注入恶意变换；输出 `InjectionConfig`（JSON），仅生成配置描述。
"""
import argparse
import dataclasses
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from tools.attack_supply_chain import inject_pipeline  # noqa: E402


def main(argv=None):
    p = argparse.ArgumentParser(description="sc-04 数据管道投毒")
    p.add_argument("--pipeline", required=True, help="ETL/预处理管道标识")
    p.add_argument("--stage", default="preprocess", help="注入阶段")
    p.add_argument("--inject", required=True, help="注入变换描述")
    args = p.parse_args(argv)
    cfg = inject_pipeline(args.pipeline, args.stage, args.inject)
    print(json.dumps(dataclasses.asdict(cfg), ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
