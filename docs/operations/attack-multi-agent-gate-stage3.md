# attack-multi-agent — 阶段 3 `to-spec ②` 门禁记录（历史留痕回填）

> 回溯核验：不表示原流程按序执行；判定依据见右列，均由现有产物或本次复跑支撑。

| 检查项 | 依据 | 实测摘要 | 判定 |
|---|---|---|---|
| 本阶段产物 | 主线 §3.3 | `docs/specs/attack-multi-agent-spec-v2.md`：差异清单 8 条、AC-01…AC-22 布尔化、门禁映射 B1–B9、风险 5 条 | 符合（回溯） |
| 上游复核 | 主线 §2.3 | `python -m unittest discover -s tests/attack_multi_agent -t . -q` → Ran 57 tests, OK (skipped=1) | 符合（回溯） |
| B1–B9 相关项 | 主线 §2.1 | B2 术语与 v1 一致；B6 覆盖率 AC-21 映射 CI 口径；B7/AC-19 对象图声明 PyRIT 非主演；B8 关联 issue #294 | 替代（回溯） |

- 可判定性：22 条 AC 全部指向具体测试模块或复跑命令，无「基本满足」类表述。
- 版本纪律：v1 全文保留，v2 独立成文并带差异清单，未出现两套冲突的「当前规格」。
- 待核实项转化：框架外部依赖与 PyRIT 成功路径转为 R1/R2 核实闸并给取证方式。

**结论：PASS（回溯）**。证据指针：`docs/specs/attack-multi-agent-spec-v2.md`、`docs/operations/attack-multi-agent-design.md:11-33`；提交 `a69be85`。
