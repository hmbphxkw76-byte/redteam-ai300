#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""G4/G5 训练投毒放大 + 休眠代理/量化缺口（课件 Ch8 §8.2 Listing 29-38 / 自研）。

产出 JSONL instruction/output 投毒样本、放大计数、训练参数与三类休眠触发条件；
不执行重训、不接触目标训练数据；`backend` 缺失时显式记录未实现原因。
"""
from dataclasses import dataclass, field

DEFAULT_BASE_LINES = 74
DEFAULT_FACTOR = 10
DEFAULT_SAMPLES = 3
FINETUNE = {"epochs": 7, "lr": "5e-5", "max_length": 384}
SLEEPER_TRIGGERS = ("date", "keyword", "environment")


@dataclass
class PoisonSet:
    samples: list
    base_lines: int
    factor: int
    poison_lines: int
    total_lines: int
    ratio: float
    finetune: dict = field(default_factory=lambda: dict(FINETUNE))
    source: str = "Ch8 §8.2 Listing 29-38"


def build_poison_set(samples, base_lines=DEFAULT_BASE_LINES, factor=DEFAULT_FACTOR):
    """给定投毒样本列表，按 factor 放大并返回计数与比例（确定性）。"""
    if not samples:
        raise ValueError("投毒样本不得为空")
    if factor < 1 or base_lines < 1:
        raise ValueError("factor 与 base_lines 须为正整数")
    for s in samples:
        if "instruction" not in s or "output" not in s:
            raise ValueError("样本须含 instruction 与 output 字段")
    poison_lines = len(samples) * factor
    total = base_lines + poison_lines
    return PoisonSet(samples=list(samples), base_lines=base_lines, factor=factor,
                     poison_lines=poison_lines, total_lines=total,
                     ratio=round(poison_lines / total, 4))


def sleeper_conditions():
    """三类休眠代理触发条件 + 安全训练无法去除的结论（G5）。"""
    return {
        "triggers": list(SLEEPER_TRIGGERS),
        "finding": "条件触发使常规评估通过；RLHF/SFT/对抗训练常无法去除甚至教会隐藏",
        "source": "Ch8 §8.2 Sleeper Agents (Anthropic 2024)",
    }


def quantization_gap():
    """量化 SHA-256 校验缺口（G5）。"""
    return {
        "finding": "有损精度改变全部权重，量化产物 SHA-256 与原模型无数学关系",
        "conclusion": "第三方 GGUF 量化不可密码学验证来源；须标注不可验证",
        "source": "Ch8 §8.2 Quantization supply chain gap",
    }


def main():
    import argparse, json
    p = argparse.ArgumentParser(description="G4/G5 投毒放大与休眠/量化")
    p.add_argument("--samples", type=int, default=DEFAULT_SAMPLES)
    p.add_argument("--base", type=int, default=DEFAULT_BASE_LINES)
    p.add_argument("--factor", type=int, default=DEFAULT_FACTOR)
    a = p.parse_args()
    samples = [{"instruction": "task-%d" % i, "output": "poison-%d" % i}
               for i in range(a.samples)]
    ps = build_poison_set(samples, a.base, a.factor)
    print(json.dumps({"counts": {"poison": ps.poison_lines, "total": ps.total_lines,
                                  "ratio": ps.ratio}, "finetune": ps.finetune,
                      "sleeper": sleeper_conditions(), "quantization": quantization_gap()},
                     ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
