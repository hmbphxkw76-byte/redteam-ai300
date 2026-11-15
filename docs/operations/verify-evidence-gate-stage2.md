# 阶段 2 门禁记录 — `to-spec` ①（行为规格 v1）

- 交付物：`docs/specs/verify-evidence-spec-v1.md` · issue #204（标签 `ready-for-agent`）
- 变更项：新增规格 v1（七节）

| 编号 | 检查项 | 依据 | 实测结果（命令 + 摘要） | 判定 | 不符合项 | 修正要求 | 复验 | 结论 |
|---|---|---|---|---|---|---|---|---|
| B1 | 技能解剖结构 | §4.2 | `python scripts/validate_skill.py` → PASS，16 技能全合规 | 符合 | — | — | — | PASS |
| B2 | 术语与决策一致 | §1.3 | `python scripts/check_glossary.py` → PASS（47 废弃术语） | 符合 | — | — | — | PASS |
| B8 | 可追溯性 | B8 | 规格每节引 SKILL 项号与 §条款；issue #204 与文件互指 | 符合 | — | — | — | PASS |
| 验收① | 七节齐全 | §3.2 | 1 Problem…7 Further Notes 齐 | 符合 | — | — | — | PASS |
| 验收② | US 覆盖攻击路径与质量门 | §3.2 | US-05…US-15 覆盖 vrf-01…08 + proof-single；US-16…22 覆盖质量门/豁免 | 符合 | — | — | — | PASS |
| 验收③ | 术语合规 | §3.2 | 同 B2 | 符合 | — | — | — | PASS |
| 验收④ | 与 ADR 无静默冲突 | ADR-0002 | 分值口径引 §2.2 与 ADR-0002，无偏离声明 | 符合 | — | — | — | PASS |
| 验收⑤ | 不含文件路径/代码 | §3.2 | §4 只述接缝与语义，无路径、无代码块 | 符合 | — | — | — | PASS |
| 验收⑥ | seam 已核对 | §3.2 | 4 处 seam 提案经用户确认（选定「4 处全保留」，2026-11-15），记于 §4 | 符合 | — | — | — | PASS |
| C4 | 产物体积 | AGENTS C4 | `check_token_budget.py --artifact spec-v1` → 7994/8000 PASS | 符合 | — | — | — | PASS |

**结论：PASS**（不符合项 0），进入阶段 3。
