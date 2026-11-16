# 阶段 6 门禁记录 — `codebase-design`

- 交付物：`docs/operations/verify-evidence-design.md`（模块职责 / 公开接口 / 依赖方向 / 4 处 seam 与注入点 / 被否决方案 5 条）
- 变更项：新增设计记录；无代码改动

| 编号 | 检查项 | 依据 | 实测结果（命令 + 摘要） | 判定 | 不符合项 | 修正要求 | 复验 | 结论 |
|---|---|---|---|---|---|---|---|---|
| B2 | 术语一致 | §1.3 | `check_glossary.py` → PASS（50 术语） | 符合 | — | — | — | PASS |
| B7 | 无旧版 PyRIT 对象 | B7 | `grep -nE "pyrit\.orchestrator|Orchestrator|AzureOpenAIChatTarget" docs/operations/verify-evidence-design.md` → 无匹配 | 符合 | — | — | — | PASS |
| B8 | 可追溯性 | B8 | 设计表逐条标 AC/缺口编号；被否决方案 5 条各带理由 | 符合 | — | — | — | PASS |
| 验收① | seam 数量与位置明确 | §3.6 | S-1…S-4 四处，与 v1 §4 一致；§4 表给位置与注入方式 | 符合 | — | — | — | PASS |
| 验收② | 接口职责/输入/输出/错误 | §3.6 | §2 表 8 行，四列齐全 | 符合 | — | — | — | PASS |
| 验收③ | 依赖方向单向 | §3.6 | §3 图：main→verify→checks→注入能力；无反向边 | 符合 | — | — | — | PASS |
| 验收④ | 测试替身可替换 | §3.6 | §4 表列四类替身 | 符合 | — | — | — | PASS |
| 验收⑤ | 与 ADR 无冲突 | ADR-0002/0004 | §6 显式说明 | 符合 | — | — | — | PASS |
| seam 增量 | 理由记录 | §3.6 | seam 未增加（沿用 v1）；拆包方案被否决理由见 §5 | 符合 | — | — | — | PASS |

**结论：PASS**（不符合项 0），进入阶段 7。
