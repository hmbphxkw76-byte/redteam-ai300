#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""计分排序：按 GOVERNANCE §2.2/§2.3 对富化资产排序（杠杆优先）。"""
from .model import DECOY


def score_and_rank(assets):
    """返回按分值降序排列的全部资产（含诱饵 0 分置底，便于 §1 计分排序节）。

    排序：AI向量机=独立机(15) ≥ 传统向量机(10) > 域控/链式入口(5) > 诱饵机(0)。
    """
    return sorted(assets, key=lambda a: a.rank_key())


def high_value_only(assets):
    """剔除诱饵后的高价值资产（用于质量门判定）。"""
    return [a for a in score_and_rank(assets) if not a.is_decoy]
