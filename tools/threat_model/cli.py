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
    ap.add_argument("--roe", default=None,
                    help="RoE 约束 JSON（S-4 规则注入，硬过滤双轨）")
    ap.add_argument("--prior", default=None,
                    help="上一版威胁模型 markdown/JSON（S-5 历史注入，增量重建）")
    ap.add_argument("--brief-out", default=None,
                    help="六段攻击情报简报输出路径（Ch10 Listing 8）")
    args = ap.parse_args(argv)

    try:
        with open(args.inventory, "r", encoding="utf-8") as f:
            inv = json.load(f)
        with open(args.classification, "r", encoding="utf-8") as f:
            cls = json.load(f)
        roe = None
        if args.roe:
            with open(args.roe, "r", encoding="utf-8") as f:
                roe = json.load(f)
        prior = None
        if args.prior:
            with open(args.prior, "r", encoding="utf-8") as f:
                prior_data = json.load(f)
            prior = _prior_from_dict(prior_data)
    except (OSError, ValueError) as exc:
        print("ERROR: 读取输入失败：%s" % exc, file=sys.stderr)
        return 1

    tm = build_threat_model(inv, cls, roe=roe, prior=prior)
    markdown = render(tm)
    missing = tm.quality_gate()

    if args.out == "-":
        sys.stdout.write(markdown)
    else:
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(markdown)
        print("已生成威胁模型：%s" % args.out)

    if args.brief_out:
        from .brief import render_brief
        with open(args.brief_out, "w", encoding="utf-8") as f:
            f.write(render_brief(tm))
        print("已生成攻击情报简报：%s" % args.brief_out)

    if missing:
        print("质量门未过（缺：%s）" % "、".join(missing), file=sys.stderr)
        return 1
    return 0


def _prior_from_dict(data):
    """从 JSON 重建最小 prior ThreatModel（供增量重建，保留已验证假设）。"""
    from .model import ThreatModel, Assumption
    assumptions = [Assumption(**{k: v for k, v in a.items()
                                 if k in Assumption.__dataclass_fields__})
                   for a in data.get("assumptions", [])]
    return ThreatModel(
        target=data.get("target", ""),
        high_value=[], boundaries={}, paths=[], decoys=[],
        graph={}, order=[],
        assumptions=assumptions,
        revision=int(data.get("revision", 1)),
        decision_log=list(data.get("decision_log", [])),
    )


if __name__ == "__main__":
    sys.exit(main())
