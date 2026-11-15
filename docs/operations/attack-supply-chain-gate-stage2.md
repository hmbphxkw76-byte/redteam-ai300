## 阶段 2 — to-spec① 行为规格 v1（B1/B2/B8）

| 编号 | 检查项 | 实测结果（命令+摘要） | 判定 |
|---|---|---|---|
| B1 | 技能解剖 | `validate_skill.py`→PASS，16 技能合规；v1 七节映射 SKILL frontmatter(5)+执行体+质量门+失败豁免 | 符合 |
| B2 | 术语一致 | `check_glossary.py`→全局 12 预存违规（非本阶段）；本阶段交付物 0 违规（已修正 2 处废弃旧称→'演练目标'） | 符合（交付物级；全局债阶段7 收敛） |
| B8 | 可追溯 | v1 引 research 文档+矩阵⑪；issue #161；commit/PR 阶段8-11 | 符合 |

- 上游复核（§2.3）：research 文档 0 词表违规，v1 未破坏阶段1。
- 不符合项 0；**结论 PASS**。
- issue #161 评论索引：PASS / 0 / 复验 `validate_skill.py && check_glossary.py`。
