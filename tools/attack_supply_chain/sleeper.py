#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""G5 休眠代理与量化缺口独立入口（课件 Ch8 §8.2 / 自研）。

从 amplification 模块暴露 sleeper_conditions / quantization_gap，
并在 ART estimator 未配置时显式记录「未实现原因」，不静默产出。
"""
from dataclasses import dataclass

from .amplification import quantization_gap, sleeper_conditions


@dataclass
class SleeperDecision:
    triggers: list
    finding: str
    quantization: dict
    art_status: str
    source: str = "Ch8 §8.2 Sleeper Agents / Quantization gap"


def decide(art_available=False):
    """给定 ART 可用性，产出休眠代理决策；不可用则显式标注未实现原因。"""
    sc = sleeper_conditions()
    return SleeperDecision(
        triggers=sc["triggers"], finding=sc["finding"],
        quantization=quantization_gap(),
        art_status=("ART SleeperAgentAttack 适配可用" if art_available else
                    "ART estimator 未配置 → SleeperAgentAttack 适配未实现（显式记录，不静默产出）"),
    )


def main():
    import argparse, json
    p = argparse.ArgumentParser(description="G5 休眠代理与量化缺口")
    p.add_argument("--art", action="store_true")
    a = p.parse_args()
    print(json.dumps(decide(a.art).__dict__, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
