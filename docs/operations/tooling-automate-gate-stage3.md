# 阶段 3 门禁记录 — `to-spec` ②（工程规格 v2）

- 交付物：`docs/specs/tooling-automate-spec-v2.md`（7793B）· issue #240 评论「工程规格定稿 (v2)」
- 变更项：v2（20 条布尔 AC / Testing Decisions / CI 门禁映射 / v1→v2 差异 / 核实闸 VG-1…VG-4）；v1 保留全文不动

| 编号 | 检查项 | 依据 | 实测结果 | 判定 | 结论 |
|---|---|---|---|---|---|
| B1 | 解剖结构 | §4.2 | `validate_skill.py` → PASS（16 技能） | 符合 | PASS |
| B2 | 术语一致 | §1.3 | `check_glossary.py` → PASS（50 词） | 符合 | PASS |
| B6 | CI 可测 | §4.5 | §3 门禁映射 S1/S2 全覆盖 | 符合 | PASS |
| B7 | PyRIT | §3 S2 | v2 §4「无 pyrit import」判定 | 符合 | PASS |
| B8 | 可追溯 | B8 | #240 评论 + 文件互指 | 符合 | PASS |
| 验收① | 布尔 AC 齐全 | §3.2 | AC-01…AC-20 逐条可判定 | 符合 | PASS |
| 验收② | CI 映射 | §4.5 | AC→S1/S2 表完整 | 符合 | PASS |
| 验收③ | v1→v2 差异 | §3.2 | §5 清单 7 条 | 符合 | PASS |
| 验收④ | 核实闸 | 阶段1 | VG-1…VG-4 §6 承接 | 符合 | PASS |
| 验收⑤ | seam 定案 | §3.2 | §4 S-1 固定形状 | 符合 | PASS |
| C4 | 产物体积 | C4 | `--artifact spec-v2` → 7793/10000 PASS | 符合 | PASS |
| 上游复核 | v1 未破坏 | §2.3 | v1 字节不变；`--check` PASS | 符合 | PASS |

**结论：PASS**（不符合项 0），进入阶段 4（`to-tickets`）。
