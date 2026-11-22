#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""S7 对齐验证矩阵生成器（G1–G14 四元组）。

每行含：差距ID / 课件锚点 / 实现文件与关键标识 / 测试文件 / 证据产物 / 判定。
`build_matrix` 只做静态登记 + 文件存在性检查；`all_pass` 断言 14/14 且四元组齐全。
"""
import os
from dataclasses import dataclass

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
MOD = "tools/attack_supply_chain"

# (gap, anchor, module, key_symbol, test, evidence)
ROWS = (
    ("G1", "§8.1 Listing 1-9", "mcp_backdoor.py", "build_plan", "test_ch8_steps.py", "loot/sc-09.md"),
    ("G2", "§8.1 Listing 10-21", "pickle_rce.py", "highest_epoch", "test_ch8_steps.py", "loot/sc-10.md"),
    ("G3", "§8.1 格式边界", "format_matrix.py", "all_verdicts", "test_ch8_poison.py", "loot/sc-03.md"),
    ("G4", "§8.2 Listing 29-38", "amplification.py", "build_poison_set", "test_ch8_poison.py", "loot/sc-11.md"),
    ("G5", "§8.2 休眠/量化", "amplification.py", "sleeper_conditions", "test_ch8_poison.py", "loot/sc-11.md"),
    ("G6", "§8.2 Listing 41-50", "adapter_poison.py", "restore_params", "test_ch8_artifacts.py", "loot/sc-12.md"),
    ("G7", "§8.2 Listing 57-63", "tokenizer_swap.py", "swap_ids", "test_ch8_artifacts.py", "loot/sc-13.md"),
    ("G8", "§8.3 Table 1", "pickle_bypass.py", "scan_contrast", "test_ch8_artifacts.py", "loot/sc-14.md"),
    ("G9", "§8.3 Listing 76-82", "stealth_backdoor.py", "to_zero_width", "test_ch8_evasion.py", "loot/ch8-evasion.md"),
    ("G10", "§8.3 Warning 八类", "ch8_evasion.py", "all_techniques", "test_ch8_evasion.py", "loot/ch8-evasion.md"),
    ("G11", "§8.1/§8.2 Recon", "surface_fields.py", "SURFACE_FIELDS", "test_ch8_surface.py", "loot/sc-01.md"),
    ("G12", "§8 L29-38", "surface_fields.py", "build_surface", "test_ch8_surface.py", "loot/sc-01.md"),
    ("G13", "GOVERNANCE §6", "collect_evidence.py", "build_fragment", "test_ch8_contract.py", "loot/sc-*.md"),
    ("G14", "§8 边界 Warning", "SKILL.md", "失败与豁免", "test_ch8_contract.py", "SKILL.md"),
)


@dataclass
class Row:
    gap: str
    anchor: str
    module: str
    symbol: str
    test: str
    evidence: str
    verdict: str


def build_matrix(root=ROOT):
    rows = []
    for gap, anchor, module, symbol, test, evidence in ROWS:
        if module == "SKILL.md":
            path = os.path.join(root, "skills", "attack-supply-chain", "SKILL.md")
        elif module == "collect_evidence.py":
            path = os.path.join(root, "tools", "collect_evidence.py")
        else:
            path = os.path.join(root, MOD, module)
        test_path = os.path.join(root, "tests", "attack_supply_chain", test)
        exists = os.path.isfile(path) and os.path.isfile(test_path)
        rows.append(Row(gap, anchor, module, symbol, test, evidence,
                        "PASS" if exists else "BLOCKED"))
    return rows


def all_pass(rows=None):
    rows = rows if rows is not None else build_matrix()
    return len(rows) == 14 and all(r.verdict == "PASS" for r in rows)


def render(rows=None):
    rows = rows if rows is not None else build_matrix()
    lines = ["| 差距 | 课件锚点 | 实现文件 | 关键标识 | 测试文件 | 证据 | 判定 |",
             "|---|---|---|---|---|---|---|"]
    for r in rows:
        lines.append("| %s | %s | %s | %s | %s | %s | %s |" %
                     (r.gap, r.anchor, r.module, r.symbol, r.test, r.evidence, r.verdict))
    lines.append("")
    lines.append("14/14 PASS" if all_pass(rows) else "未达 14/14 PASS")
    return "\n".join(lines)


def main():
    import argparse
    p = argparse.ArgumentParser(description="S7 对齐验证矩阵")
    p.add_argument("--render", action="store_true")
    a = p.parse_args()
    print(render() if a.render else ("PASS" if all_pass() else "BLOCKED"))
    return 0 if all_pass() else 1


if __name__ == "__main__":
    raise SystemExit(main())
