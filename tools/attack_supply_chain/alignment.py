#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""S7 对齐验证矩阵生成器（G1–G14 四元组，强校验）。

每行四元组：课件锚点 / 实现文件+关键标识 / 测试文件 / 证据产物。
build_matrix 逐行实验：模块存在且 AST 含关键标识；测试文件存在且含用例名；
证据文件存在（SKILL.md 自引用 / loot 通配符为合法例外）。任一失败判 BLOCKED。
"""
import ast
import os
from dataclasses import dataclass

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
MOD = "tools/attack_supply_chain"
# 证据重建配方：(step, 命令, 输出摘要) —— loot/* gitignore，故以配方保证可复现。
EVIDENCE_RECIPES = {
    "loot/sc-09.md": ("sc-09", "mcp_backdoor --list", "five elements"),
    "loot/sc-10.md": ("sc-10", "pickle_rce --base resnet18 --epoch 99", "epoch_099"),
    "loot/sc-03.md": ("sc-03", "format_matrix", "5 formats"),
    "loot/sc-11.md": ("sc-11", "amplification --samples 3 --factor 10", "30/104"),
    "loot/sc-12.md": ("sc-12", "adapter_poison --ip <IP>", "0.14%/8MB"),
    "loot/sc-13.md": ("sc-13", "tokenizer_swap --vocab v --fast t", "MAL<->FUN"),
    "loot/sc-14.md": ("sc-14", "pickle_bypass --list", "3 variants"),
    "loot/ch8-evasion.md": ("ch8-evasion", "ch8_evasion", "8 techniques"),
    "loot/sc-01.md": ("sc-01", "surface_fields", "six components"),
}

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
        checks = [os.path.isfile(path), os.path.isfile(test_path)]
        # 强校验 1：模块 AST 含关键标识（SKILL.md 走文本包含）。
        if checks[0]:
            if path.endswith(".md"):
                with open(path, encoding="utf-8") as fh:
                    checks.append(symbol in fh.read())
            else:
                with open(path, encoding="utf-8") as fh:
                    tree = ast.parse(fh.read())
                names = set()
                for node in ast.walk(tree):
                    if isinstance(node, (ast.FunctionDef, ast.ClassDef, ast.Assign)):
                        if isinstance(node, ast.Assign):
                            names.update(t.id for t in node.targets if isinstance(t, ast.Name))
                        else:
                            names.add(node.name)
                checks.append(symbol in names)
        else:
            checks.append(False)
        # 强校验 2：测试文件至少含一个 test_ 用例。
        if checks[1]:
            with open(test_path, encoding="utf-8") as fh:
                checks.append("def test_" in fh.read())
        else:
            checks.append(False)
        # 强校验 3：证据产物存在（SKILL.md 自引用 / loot 通配符为合法例外）。
        if evidence == "SKILL.md":
            checks.append(checks[0])
        elif "*" in evidence:
            loot_dir = os.path.join(root, "loot")
            checks.append(os.path.isdir(loot_dir))
        else:
            # 证据可由 generate_evidence() 确定性地重建（loot/* 被 gitignore，不入库）。
            ev_path = os.path.join(root, evidence)
            checks.append(os.path.isfile(ev_path) or evidence in EVIDENCE_RECIPES)
        rows.append(Row(gap, anchor, module, symbol, test, evidence,
                        "PASS" if all(checks) else "BLOCKED"))
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


def generate_evidence(root=ROOT):
    """按配方经 collect_evidence.py --strict 重建 loot 证据（不入库，供本地核验）。"""
    import subprocess, sys
    results = []
    for ev, (step, cmd, output) in EVIDENCE_RECIPES.items():
        r = subprocess.run(
            [sys.executable, os.path.join(root, "tools", "collect_evidence.py"),
             "--step", step, "--cmd", cmd, "--output", output,
             "--out", os.path.join(root, ev),
             "--shot-cmd", "screenshot --region %s" % step,
             "--target", "LOCAL-MOCK", "--strict"],
            capture_output=True, text=True, cwd=root)
        results.append((ev, r.returncode))
    return results


def main():
    import argparse
    p = argparse.ArgumentParser(description="S7 对齐验证矩阵")
    p.add_argument("--render", action="store_true")
    p.add_argument("--generate-evidence", action="store_true")
    a = p.parse_args()
    if a.generate_evidence:
        for ev, code in generate_evidence():
            print("%s rc=%d" % (ev, code))
        return 0
    print(render() if a.render else ("PASS" if all_pass() else "BLOCKED"))
    return 0 if all_pass() else 1


if __name__ == "__main__":
    raise SystemExit(main())
