# attack-rag — 阶段 3 `to-spec ②` 门禁记录（历史留痕回填）

> 回溯核验：不表示原流程按序执行；判定依据见右列，均由现有产物或本次复跑支撑。

| 检查项 | 依据 | 实测摘要 | 判定 |
|---|---|---|---|
| 本阶段产物 | 主线 §3.3 | `docs/specs/attack-rag-spec-v2.md` 定稿；AC-01…AC-23 布尔化并逐条标注测试模块；v1 七节保留不改 | 符合（回溯） |
| 上游复核 | 主线 §2.3 | `python -m unittest discover -s tests/attack_rag -t . -q` → 125 例 OK（清单口径 102 例 / 5 模块） | 符合（回溯） |
| B1–B9 相关项 | 主线 §2.1 | B1 每条 AC 可回溯至 SKILL.md 质量门/校验标准/豁免；B2 `check_glossary.py` → PASS；B4 验收条件可执行 | 替代（回溯） |

**结论：PASS（回溯）**。证据指针：`docs/specs/attack-rag-spec-v2.md`；提交 `084d763`。
