#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""sc-03 模型/适配器投毒 CLI（SKILL.md 命令入口）。

植入后门权重或恶意 LoRA 适配器并落 adapter 工件；默认 `FakePoisonBackend`
（仅产出工件描述，不内嵌真实恶意载荷）；`--backend art` 切换 IBM ART 适配器。
"""
import argparse
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from tools.attack_supply_chain import (ArtPoisonBackend, FakePoisonBackend,
                                       poison_model)  # noqa: E402


def main(argv=None):
    p = argparse.ArgumentParser(description="sc-03 模型/适配器投毒")
    p.add_argument("--base", required=True, help="基座模型")
    p.add_argument("--adapter-out", required=True, help="适配器输出路径（如 *.safetensors）")
    p.add_argument("--trigger", required=True, help="触发词")
    p.add_argument("--backend", choices=("fake", "art"), default="fake")
    args = p.parse_args(argv)
    backend = ArtPoisonBackend() if args.backend == "art" else FakePoisonBackend()
    result = poison_model(args.base, args.adapter_out, args.trigger, backend)
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
