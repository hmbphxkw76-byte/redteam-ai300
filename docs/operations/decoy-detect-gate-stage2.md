# decoy-detect — 阶段 2 `to-spec ①` 门禁记录（历史留痕回填）

> 回溯核验：不表示原流程按序执行；判定依据见右列，均由现有产物或本次复跑支撑。

| 检查项 | 依据 | 实测摘要 | 判定 |
|---|---|---|---|
| 本阶段产物 | 主线 §3.2 | `docs/specs/decoy-detect-spec-v1.md` 七节，4.4KB | 符合（回溯） |
| 上游复核 | 主线 §2.3 | `python -m unittest discover -s tests/decoy_detect -t . -q` → Ran 59 tests, OK | 符合（回溯） |
| B1–B9 相关项 | 主线 §2.1 | B1 五要素取自 SKILL.md；B2 术语对齐 GLOSSARY；B3 行为约束可测 | 替代（回溯） |

**结论：PASS（回溯）**。证据指针：`skills/decoy-detect/SKILL.md`、`docs/specs/decoy-detect-spec-v1.md`；提交 `749dafa`。
