## 阶段 6 — codebase-design（B2/B7/B8）

| 编号 | 检查项 | 实测结果（命令+摘要） | 判定 |
|---|---|---|---|
| B2 | 术语一致 | `check_glossary.py`→设计文件 0 违规 | 符合 |
| B7 | PyRIT 对象 | grep 仅命中"禁止 orchestrator"排除句；设计明确 PyRIT 仅 SQLiteMemory，无旧对象 | 符合 |
| B8 | 可追溯 | 设计引 spec #161 + 工单 #173-176；seam S1-S5 与阶段2 提案一致，新增 S2/S3/S4 有理由 | 符合 |

- seam：S1 证据(复用)、S2 投毒引擎、S3 扫描、S4 注入器、S5 recon 输入；新增 3 个（S2/S3/S4），理由见设计 §4。
- 依赖方向单向（workflow→seams）；外部重依赖惰性导入，可注入替身。
- 对象图无旧对象（`assessment`）；无硬编码凭据。
- 不符合项 0；**结论 PASS**。
- 复验命令：`python scripts/check_glossary.py`（设计文件 0 命中）；`grep -n orchestrator docs/operations/attack-supply-chain-design.md`（仅排除句）。
