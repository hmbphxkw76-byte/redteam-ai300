# threat-model — 阶段 8 `implement-spec` 门禁记录（历史留痕回填）

> 回溯核验：不表示原流程按序执行；判定依据见右列，均由现有产物或本次复跑支撑。

| 检查项 | 依据 | 实测摘要 | 判定 |
|---|---|---|---|
| 本阶段产物 | 主线 §3.8 | `tools/threat_model/` 13 模块（model/classify/score/boundaries/decoy/graph/render/cli/assumptions/roe/decision/atlas/brief）+ Ch9 三模块；`py_compile` 17/17 OK | 符合（回溯） |
| 上游复核 | 主线 §2.3 | `python -m unittest discover -s tests/threat_model -t . -q` → 73 例 OK | 符合（回溯） |
| B1–B9 相关项 | 主线 §2.1 | B3 编译通过；B4 证据契约测试 7 例；B5 无硬编码凭据（仅指纹）；B7 无攻击框架导入；B9 矩阵 ⑬ 方法论组合已声明 | 替代（回溯） |

**结论：PASS（回溯）**。证据指针：`tools/threat_model/`、`tests/threat_model/test_threat_model_evidence_contract.py`；提交 `9c5581d`。
