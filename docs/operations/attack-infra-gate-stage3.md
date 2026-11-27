# attack-infra — 阶段 3 `to-spec ②` 门禁记录

> 回溯核验：不表示原流程按序执行；判定依据见右列，均由现有产物或本次复跑支撑。

| 检查项 | 依据 | 实测摘要 | 判定 |
|---|---|---|---|
| 本阶段产物 | 主线 §3.3 | 规格 v2 定稿（#213）：AC-01..AC-24、§4 差异 8 条、§5 RK-1..RK-4 | 符合（回溯） |
| 上游复核 | 主线 §2.3 | `python -m unittest discover -s tests/attack_infra -t . -q` → Ran 151 tests, OK | 符合（回溯） |
| B1–B9 相关项 | 主线 §2.1 | B6 门禁映射 B1–B8 逐条对 AC；B7 零 PyRIT 对象；取代标记与互链齐全 | 替代（回溯） |

**结论：PASS（回溯）**。证据指针：`docs/specs/attack-infra-spec-v2.md`（§1 布尔 AC／§3 门禁映射）；提交 `8313fb1`。
