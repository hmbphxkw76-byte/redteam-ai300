# attack-infra — 阶段 6 `codebase-design` 门禁记录

> 回溯核验：不表示原流程按序执行；判定依据见右列，均由现有产物或本次复跑支撑。

| 检查项 | 依据 | 实测摘要 | 判定 |
|---|---|---|---|
| 本阶段产物 | 主线 §3.6 | 4 个 seam：命令执行器 `command.py`、传输 `transport.py`、证据写入器 `evidence.py`、截图 `shot.py`（仅出计划）；14 模块、单一注入点 `RunContext` | 符合（回溯） |
| 上游复核 | 主线 §2.3 | `python -m unittest discover -s tests/attack_infra -t . -q` → Ran 151 tests, OK | 符合（回溯） |
| B1–B9 相关项 | 主线 §2.1 | B7 对象图声明无 PyRIT，`grep` 旧版对象名零命中；B2 术语与 `GLOSSARY.md` 一致 | 替代（回溯） |

**结论：PASS（回溯）**。证据指针：`docs/operations/attack-infra-design.md`（§2 模块表／§4 seam 表）；提交 `8313fb1`。
