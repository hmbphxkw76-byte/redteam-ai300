#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""G11/G12 供应链面字段（课件 Ch8 §8 L17-40 / 自研）。

从 recon 资产清单抽取六组件信任面 + AI BOM 字段 + 三案例映射；
只读、不发起攻击、不改 recon-ai 七字段契约。
"""
from dataclasses import dataclass, field

SIX_COMPONENTS = ("training data", "models", "software", "infrastructure",
                  "hardware", "third-party services")
CASES = (
    ("JFrog 2024", "HF 上 100+ 恶意模型，Pickle 内嵌反弹 shell", "models / software"),
    ("NullBulge", "GitHub/HF 投毒数据集并分发恶意软件", "training data / third-party services"),
    ("Unit42 2025", "模型命名空间重注册使流水线静默拉取被投毒模型", "models / infrastructure"),
)
# NIST AML 战术 ID 映射（课件 §8 NSA CIS 指向 NIST 对抗性 ML 分类法）。
AML_TACTICS = {
    "training data": "AML.T0020 Poison Training Data",
    "models": "AML.T0010 ML Supply Chain Compromise",
    "software": "AML.T0010 ML Supply Chain Compromise",
    "infrastructure": "AML.T0040 Inference API Access",
    "hardware": "AML.T0010 ML Supply Chain Compromise",
    "third-party services": "AML.T0010 ML Supply Chain Compromise",
}
SURFACE_FIELDS = ("gitlab_group_permissions", "group_writable_dirs",
                  "shared_model_dirs", "config_model_paths", "config_tokenizer_paths")


@dataclass
class SupplySurface:
    six_components: dict
    ai_bom: dict
    cases: list
    extra_fields: dict = field(default_factory=dict)


def build_surface(assets=None):
    """给定 recon 资产 dict（可空），产出六组件 + AI BOM + 三案例 + 只读扩展字段。"""
    assets = assets or {}
    extra = {name: assets.get(name, "未提供") for name in SURFACE_FIELDS}
    return SupplySurface(
        six_components={c: {"trust_boundary": "由 recon 资产清单确认（%s）" % (assets.get(c) or "未提供"),
                            "endpoint": assets.get(c, ""), "aml_tactic": AML_TACTICS[c]}
                        for c in SIX_COMPONENTS},
        ai_bom={"components": list(SIX_COMPONENTS),
                "source": "Ch8 §8 NSA CIS 2026-03 AI BOM 建议",
                "visibility": "全链可见性（每组件记录来源与哈希）"},
        cases=[{"name": n, "fact": f, "components": c} for n, f, c in CASES],
        extra_fields=extra,
    )


def main():
    import argparse, json
    p = argparse.ArgumentParser(description="G11/G12 供应链面字段")
    p.parse_args()
    s = build_surface()
    print(json.dumps({"six_components": s.six_components, "ai_bom": s.ai_bom,
                      "cases": s.cases, "extra_fields": s.extra_fields}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
