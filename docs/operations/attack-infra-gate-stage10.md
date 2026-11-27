# attack-infra — 阶段 10 `code-review` 门禁记录

> 回溯核验：不表示原流程按序执行；判定依据见右列，均由现有产物或本次复跑支撑。

| 检查项 | 依据 | 实测摘要 | 判定 |
|---|---|---|---|
| 本阶段产物 | 主线 §3.10 | 双轴并列（基线 `fde51a1`）：Standards 8 项发现、Spec 9 项，硬违规 8+2；最严重 AC-07 为假（`impact()` 未受 `--allow-inference` 约束），已加守卫 | 符合（回溯） |
| 上游复核 | 主线 §2.3 | 审查记录 §4 复跑：`python -m unittest discover -s tests` → Ran 655 tests, OK（skipped=2） | 符合（回溯） |
| B1–B9 相关项 | 主线 §2.1 | 硬违规清零后复跑：覆盖率 1354/1487 = 91.1%；`check_glossary.py` PASS；`shell=True` 与禁用名 0 命中 | 替代（回溯） |

**结论：PASS（回溯）**。证据指针：`docs/operations/attack-infra-code-review.md`（§1 两轴结论／§2 修复清单）；提交 `8313fb1`。
