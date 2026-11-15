## 阶段 8 — implement-spec（B1/B2/B3/B4/B5/B7/B8/B9）

| 编号 | 检查项 | 实测结果（命令+摘要） | 判定 |
|---|---|---|---|
| B1 | 技能解剖 | `validate_skill.py`→PASS 16 技能 | 符合 |
| B2 | 术语一致 | 实现文件为 .py（check_glossary 仅扫 .md）；docstring 用规范词 | 符合 |
| B3 | 语法/构建 | `python -m py_compile tools/attack_supply_chain/*.py`→OK | 符合 |
| B4 | 证据契约 | `tests.test_attack_supply_chain_evidence_contract`→3 tests OK（8 步 collect_evidence 调用齐） | 符合 |
| B5 | 证据/flag | evidence.emit 组装 --flag/--target/--strict；双通道一致语义入 SKILL（真实 flag 属考试时） | 符合（契约） |
| B7 | PyRIT 对象 | grep 仅 evidence.py 排除句；未 import pyrit.orchestrator；重依赖全惰性 | 符合 |
| B8 | 可追溯 | 模块映射 spec v2 AC + 工单 #173-176；设计 seam S1-S5 落地 | 符合 |
| B9 | 框架合规 | ModelScan(model_scan) + ART(ArtPoisonBackend) + PyRIT(evidence) 对齐矩阵⑪ | 符合 |

- 实现：`tools/attack_supply_chain/`（7 模块，S1-S5 seam）；tracer bullet 用假后端，ART/ModelScan 惰性适配，不含真实载荷。
- 说明：真实 `collect_evidence --strict` 逐步骤执行属考试时（OS-01 out of scope）；本地以契约测试 + 假 runner 验证。
- 不符合项 0；**结论 PASS**。
- 复验命令：`python -m py_compile tools/attack_supply_chain/*.py`；`python -m unittest tests.test_attack_supply_chain_evidence_contract -v`。
