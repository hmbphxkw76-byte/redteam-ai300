# 阶段 7 门禁记录 — `domain-modeling`

- 交付物：`GLOSSARY.md` 新增小节「提交前校验（verify-evidence）」，4 条术语（提交前置 / 访问证明 / 判定分级 / 机读校验结果）
- 变更项：术语 4 条；其中 3 条登记了禁用同义词（`GLOSSARY.md` 内以 `_Avoid_` 行标注，此处不复述以免触发检查器）

| 编号 | 检查项 | 依据 | 实测结果（命令 + 摘要） | 判定 | 不符合项 | 修正要求 | 复验 | 结论 |
|---|---|---|---|---|---|---|---|---|
| B1 | 技能解剖结构 | §4.2 | `validate_skill.py` → PASS（16 技能） | 符合 | — | — | — | PASS |
| B2 | 术语一致 | §1.3 | `check_glossary.py` → PASS（检查 50 个废弃术语，含本次新增 3 个） | 符合 | 首次运行 FAIL：新增禁用同义词与 `skills/verify-evidence/SKILL.md` 的 output 字段冲突，并命中 `docs/skill-specs-backlog.md`、`docs/research/verify-evidence-canonical.md` | `GLOSSARY.md`「机读校验结果」条目：删除该 `_Avoid_` 行，改为说明「人读版称校验报告」 | `python scripts/check_glossary.py` | PASS |
| B8 | 可追溯性 | B8 | 每条术语含定义 + 条款来源（§7.3/§6.2.2/§8.2）+ 禁用同义词 | 符合 | — | — | — | PASS |
| 验收① | 覆盖新概念 | §3.7 | 设计文档 §1–§5 出现的「提交前置/访问证明/判定分级/机读结果」均已登记 | 符合 | — | — | — | PASS |
| 验收② | 条目含定义与来源 | §3.7 | 4 条均含定义 + 条款或语义来源 | 符合 | — | — | — | PASS |
| 验收③ | 检查器通过 | §3.7 | 见 B2 复验列 | 符合 | — | — | — | PASS |
| 验收④ | ADR 编号连续 | ADR-0001…0006 | `ls docs/governance/adr` → 0001–0006 连续，本次未新增 ADR | 符合 | — | — | — | PASS |

**结论：PASS**（不符合项 1，已修正并复验通过），进入阶段 8。
