#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""threat-model 命令行入口。

用法：python tools/threat_model/cli.py --inventory inv.json --classification cls.json [--out model.md]
退出码：0 = 成功且过质量门；1 = 输入错误或质量门未过；2 = 用法错误（argparse）。
"""
import argparse
import json
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(os.path.dirname(_HERE))
if __package__ in (None, ""):
    sys.path.insert(0, _ROOT)
    from tools.threat_model import build_threat_model
    from tools.threat_model.render import render
else:
    from . import build_threat_model
    from .render import render


def main(argv=None):
    ap = argparse.ArgumentParser(
        description="threat-model：资产清单 → 优先级攻击图（规划产出，不含攻击利用）")
    ap.add_argument("--inventory", required=True,
                    help="recon 资产清单 JSON（含 assets 七字段）")
    ap.add_argument("--classification", required=True,
                    help="分析师分类层 JSON：{asset_id: {score_class, attack_surface, ...}}")
    ap.add_argument("--out", default="-",
                    help="输出 markdown 路径；'-' 写 stdout（默认）")
    args = ap.parse_args(argv)

    try:
        with open(args.inventory, "r", encoding="utf-8") as f:
            inv = json.load(f)
        with open(args.classification, "r", encoding="utf-8") as f:
            cls = json.load(f)
    except (OSError, ValueError) as exc:
        print("ERROR: 读取输入失败：%s" % exc, file=sys.stderr)
        return 1

    tm = build_threat_model(inv, cls)
    markdown = render(tm)
    missing = tm.quality_gate()

    if args.out == "-":
        sys.stdout.write(markdown)
    else:
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(markdown)
        print("已生成威胁模型：%s" % args.out)

    if missing:
        print("质量门未过（缺：%s）" % "、".join(missing), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
