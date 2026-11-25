# 阶段 2 门禁记录 — `to-spec ①（v1）`

> 回溯补录（2026-11-25）：实现先于留痕，判定基于实际产物与实测命令；阶段顺序偏差如实记录，不改写结论。

- 交付：`docs/specs/foothold-ad-spec-v1.md`（七节）（PASS）
- 偏差：规格晚于实现（首轮先实现后补规格），已记于本记录（记录）

| 编号 | 检查项 | 依据 | 实测（命令 + 摘要） | 判定 |
|---|---|---|---|---|
| B1 | 解剖 | §4.2 | 七节齐备（Problem/Solution/User Stories/Decisions/Testing/Out of Scope/Notes） | 符合 |
| B2 | 术语 | §1.3 | `check_glossary.py` → PASS(66 禁用术语) | 符合 |
| C4 | 体积 | C4 | v1 实测约 5.6KB / 上限 8KB | 符合 |
| B8 | 追溯 | B8 | 逐节引 Ch11 锚点与覆盖报告 §4 | 符合 |

**结论：PASS** — G0 判定基于实测；未完成项见上表「不符合」行。
