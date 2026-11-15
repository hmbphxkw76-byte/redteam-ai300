## 阶段 7 — domain-modeling 领域术语建模（B1/B2/B8）

| 编号 | 检查项 | 实测结果（命令+摘要） | 判定 |
|---|---|---|---|
| B1 | 技能解剖 | `validate_skill.py`→PASS，16 技能合规 | 符合 |
| B2 | 术语一致 | `check_glossary.py`→全局 12 条预存违规（均非 attack-supply-chain 交付物）；`grep attack-supply-chain`→0 命中；GLOSSARY 新增 8 条供应链术语含定义+来源 | 符合 |
| B8 | 可追溯 | 术语映射表落 `docs/operations/attack-supply-chain-design.md` §6（SKILL↔框架对象↔代码标识符）；新增术语与 SKILL 用法一致（不误标旧称） | 符合 |

**新增术语（GLOSSARY `## AI 供应链`）**：AI 供应链、AI向量机、数据集投毒、模型投毒、适配器投毒、数据管道投毒、依赖投毒、构建触发。
- 关键决策：`数据投毒`/`供应链投毒` 为 SKILL 规范用词（训练数据投毒、技能标题），**不设为 _Avoid_**，避免子串误伤。
- 无新增 ADR（术语增补不改变架构决策）。
- 不符合项 0；**结论 PASS**。
- 复验命令：`python scripts/check_glossary.py`（12 预存、supply-chain 0 命中）；`python scripts/validate_skill.py`。
