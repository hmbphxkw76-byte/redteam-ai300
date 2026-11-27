# attack-multi-agent — 阶段 6 `codebase-design` 门禁记录（历史留痕回填）

> 回溯核验：不表示原流程按序执行；判定依据见右列，均由现有产物或本次复跑支撑。

| 检查项 | 依据 | 实测摘要 | 判定 |
|---|---|---|---|
| 本阶段产物 | 主线 §3.6 | 设计记录 `docs/operations/attack-multi-agent-design.md`：模块表、三缝注入点、对象图、路径顺序四段 | 符合（回溯） |
| 上游复核 | 主线 §2.3 | `python -m unittest discover -s tests/attack_multi_agent -t . -q` → Ran 57 tests, OK (skipped=1) | 符合（回溯） |
| B1–B9 相关项 | 主线 §2.1 | B7 对象图无 `pyrit.orchestrator`／`*Orchestrator`，PyRIT 仅懒导入补位；B9 组合取自矩阵 §⑩ | 替代（回溯） |

- 真实 seam：`Runtime` 注入式四依赖——`client`（生产 `UrllibHttpClient`／测试 `FakeHttpClient`）、`writer`（生产 `EvidenceWriter`／测试 `RecordingWriter`）、`capture`（`HeadlessCapture`／`NullCapture`／`FakeCapture`）、`scanner`（内建 `BuiltinAnalyzer`／`A2ASecBenchAdapter`）。
- 依赖方向：`cli → runner → (steps, a2a, grade, evidence, shot, scanner)` 单向；`poc` 仅在顶层薄壳侧复用 `a2a`，不回指 `runner`。
- 公开面收敛：包 `__init__` 只导出 `run_attack`、`Runtime`、`OBJECT_GRAPH`、数据模型与步骤常量。

**结论：PASS（回溯）**。证据指针：`docs/operations/attack-multi-agent-design.md:37-103`、`tools/attack_multi_agent/__init__.py`；提交 `a69be85`。
