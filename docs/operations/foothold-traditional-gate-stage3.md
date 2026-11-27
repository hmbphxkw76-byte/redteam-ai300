# foothold-traditional — 阶段 3 `to-spec ②` 门禁记录（历史留痕回填）

> 回溯核验：不表示原流程按序执行；判定依据见右列，均由现有产物或本次复跑支撑。

| 检查项 | 依据 | 实测摘要 | 判定 |
|---|---|---|---|
| 本阶段产物 | 主线 §3.3 | `docs/specs/foothold-traditional-spec-v2.md` 六节：v1→v2 差异清单 7 条、AC-01..AC-16、测试决策、门禁映射、证据与可观测性、风险与待验证 | 符合（回溯） |
| 上游复核 | 主线 §2.3 | `python -m unittest discover -s tests/foothold_traditional -t . -q` → 32 例 OK；v1 全文保留，v2 独立成文 | 符合（回溯） |
| B1–B9 相关项 | 主线 §2.1 | B1 七节→六节映射可追溯；B6 门禁映射逐条绑定命令；B7 无 PyRIT（矩阵 ⑦ 纯 Kali）；B8 AC 均指真实测试模块 | 替代（回溯） |

**结论：PASS（回溯）**。证据指针：`docs/specs/foothold-traditional-spec-v2.md`、`tests/foothold_traditional/`；提交 `6bdedce`。
