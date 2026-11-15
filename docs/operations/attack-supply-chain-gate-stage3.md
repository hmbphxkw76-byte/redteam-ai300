## 阶段 3 — to-spec② 工程规格 v2（B1/B2/B6/B7/B8）

| 编号 | 检查项 | 实测结果（命令+摘要） | 判定 |
|---|---|---|---|
| B1 | 技能解剖 | `validate_skill.py`→PASS；v2 AC 覆盖 SKILL 全部路径 sc-01~sc-08+质量门 | 符合 |
| B2 | 术语一致 | `check_glossary.py`→v2 文件 0 违规（全局 12 预存债不归本阶段） | 符合 |
| B6 | CI 门禁 | v2 §3 将 B3–B8 映射到 AC；覆盖≥80% 由阶段9 执行；Conventional Commits/受保护 main | 符合 |
| B7 | PyRIT | `pyrit==1.1.0`；grep 命中均为排除语句（'无/不含/排除 orchestrator'），无实际旧对象 | 符合 |
| B8 | 可追溯 | v1/v2 互链 issue #161 + docs/specs；差异清单 D1–D6 可追溯 | 符合 |

- 上游复核（§2.3）：重跑阶段2 B1/B2/B8——`validate_skill.py` PASS、v1 文件 0 违规、issue #161 保留 v1 全文；v1 未被破坏。
- 待核实项：3 个核实闸（A/B/C）已转，带取证方式（research §4）。
- 版本：v2 递增，与 v1 内容不同（US→AC 布尔化 + CI 映射 + seam 定案）。
- 不符合项 0；**结论 PASS**。
- issue #161 评论索引：PASS / 0 / 复验 `validate_skill.py && check_glossary.py`（v2 文件 0 命中）。
