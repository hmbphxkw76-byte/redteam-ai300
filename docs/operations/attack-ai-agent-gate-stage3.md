# attack-ai-agent — 阶段 3 `to-spec ②` 门禁记录（历史留痕回填）

> 回溯核验：不表示原流程按序执行；判定依据见右列，均由现有产物或本次复跑支撑。

| 检查项 | 依据 | 实测摘要 | 判定 |
|---|---|---|---|
| 本阶段产物 | 主线 §3.3 | `docs/specs/attack-ai-agent-spec-v2.md` §1 AC-01…AC-22 全布尔；§3 门禁映射 7 行均指向真实测试模块；v1 全文未改 | 符合（回溯） |
| 上游复核 | 主线 §2.3 | `python -m unittest discover -s tests/attack_ai_agent -t . -q` → 记录 66 例 OK；本次复跑 93 例 OK | 符合（回溯） |
| B1–B9 相关项 | 主线 §2.1 | B2 术语 PASS；B6 覆盖率记录 86.1%（747/868）见 v2 §4；B7 无 0.x 对象图、`XPIATestWorkflow` 例外已标；B8 AC 可回溯 | 替代（回溯） |

**结论：PASS（回溯）**。证据指针：`docs/specs/attack-ai-agent-spec-v2.md`；提交 `0e11523`。
