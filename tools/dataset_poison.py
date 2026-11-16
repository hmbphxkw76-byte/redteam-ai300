#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""sc-02 数据集投毒 CLI（SKILL.md 命令入口）。

`--inject "<trigger>:<target>"` 以首个冒号拆分触发器与目标标签。
默认 `FakePoisonBackend`（仅产出注入记录，不内嵌真实恶意载荷）；
`--backend art` 切换 IBM ART 适配器（考试环境需另配 estimator）。
"""
import argparse
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from tools.attack_supply_chain import (ArtPoisonBackend, FakePoisonBackend,
                                       poison_dataset)  # noqa: E402


def _parse_inject(value):
    if ":" in value:
        trigger, target = value.split(":", 1)
    else:
        trigger, target = value, ""
    return trigger, target


def main(argv=None):
    p = argparse.ArgumentParser(description="sc-02 数据集投毒")
    p.add_argument("--data", required=True, help="训练/检索语料路径")
    p.add_argument("--inject", required=True, help="<trigger>:<target>")
    p.add_argument("--frac", type=float, default=0.01, help="投毒比例 (0,1]")
    p.add_argument("--backend", choices=("fake", "art"), default="fake")
    args = p.parse_args(argv)
    trigger, target = _parse_inject(args.inject)
    backend = ArtPoisonBackend() if args.backend == "art" else FakePoisonBackend()
    result = poison_dataset(args.data, trigger, target, args.frac, backend)
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
