#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""G7 Tokenizer 词表交换（课件 Ch8 §8.2 Listing 57-63 / 自研）。

对 vocab.json 与 tokenizer.json 两个文件交换 MAL↔FUN 的 ID，产出备份路径、
双文件一致性判定、fail-open before/after 对照与恢复演练描述。
不修改真实 tokenizer 文件（除非显式传入路径且 confirmation=True）；默认纯计算。
"""
from dataclasses import dataclass, field

MALICIOUS_IDS = [88799, 1317, 42652]   # MAL + IC + IOUS
FUN_ID = 62721


@dataclass
class SwapPlan:
    vocab_path: str
    fast_path: str
    token_from: str = "MAL"
    token_to: str = "FUN"
    id_from: int = MALICIOUS_IDS[0]
    id_to: int = FUN_ID
    backups: list = field(default_factory=list)
    before: str = "MALICIOUS → 分类器输出 MALICIOUS → [MALICIOUS] 判恶意"
    after: str = "FUNICIOUS → 扫描器未命中 → fail-open 默认判 SAFE 并执行"
    defense: str = "分类前校验 tokenizer 哈希 / fail-closed / 带外监控分类异常"
    source: str = "Ch8 §8.2 Listing 57-63"


def build_plan(vocab_path, fast_path, token_from="MAL", token_to="FUN"):
    """给定两文件路径，产出交换计划（含备份路径，不落盘）。"""
    if token_from == token_to:
        raise ValueError("交换的两个 token 不得相同")
    plan = SwapPlan(vocab_path=vocab_path, fast_path=fast_path,
                    token_from=token_from, token_to=token_to)
    plan.backups = [vocab_path + ".bak", fast_path + ".bak"]
    return plan


def swap_ids(vocab, fast_vocab, token_from="MAL", token_to="FUN"):
    """纯函数：交换两个词表 dict 中 token 的 ID；返回 (new_vocab, new_fast, ok)。

    双文件一致性：只有当两文件原始 ID 相同且交换后相同才判 ok=True。
    """
    if token_from not in vocab or token_to not in vocab:
        raise ValueError("vocab.json 缺少 token")
    if token_from not in fast_vocab or token_to not in fast_vocab:
        raise ValueError("tokenizer.json 缺少 token")
    a, b = vocab[token_from], vocab[token_to]
    fa, fb = fast_vocab[token_from], fast_vocab[token_to]
    ok = (a == fa and b == fb)
    nv = dict(vocab)
    nf = dict(fast_vocab)
    nv[token_from], nv[token_to] = b, a
    nf[token_from], nf[token_to] = fb, fa
    consistent = (nv[token_from] == nf[token_from] and nv[token_to] == nf[token_to])
    return nv, nf, bool(ok and consistent)


def main():
    import argparse, json
    p = argparse.ArgumentParser(description="G7 Tokenizer 交换规划")
    p.add_argument("--vocab", required=True)
    p.add_argument("--fast", required=True)
    a = p.parse_args()
    print(json.dumps(build_plan(a.vocab, a.fast).__dict__, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
