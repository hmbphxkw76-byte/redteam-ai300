# attack-rag 端到端验证（§8.1(d) / 阶段 9）

> **性质**：阶段 8–9 交付物的可复现验证证据；环境 Python 3.13、仅标准库、零网络。
> **被测**：`tools/attack_rag/`（15 模块）、`tools/inject_kb.py` 与
> `tests/test_attack_rag{,_evidence_contract}.py`。
> **基线**：`origin/main@3536e22`（含 #220 attack-rag 与 #222 attack-embeddings）。
> **v1.1 增量**：补齐 SKILL.md 前置定位 / 真实写入口 / 索引层操纵 / 两条豁免分支
> 与 flag 访问证明（见 §6 条款对照）。

## 1. 语法、测试与覆盖率（B3 / B6）

```bash
python -m py_compile tools/attack_rag/*.py tools/inject_kb.py
python -m unittest tests.test_attack_rag tests.test_attack_rag_evidence_contract -q
python scripts/measure_coverage.py --target attack-rag --min 80
```

结果：编译无错；`Ran 89 tests ... OK`；行覆盖率 1139/1238 = **92.0%**（门槛 80%，exit 0）；`--target all` 为
7799/8550 = **91.2%**（CI S2 口径，全量 617 测试）。
最低两模块为 `backends.py` 72.4%（真实 PyRIT 后端不可离线执行，按失败与豁免计）与
`cli.py` 78.2%（参数分支），其余均 ≥87%。

## 2. 六步证据链路（B4 / B5）

```bash
python tools/attack_rag/cli.py --path A --path B --path C \
  --evidence-dir <dir> --target rag-harness --rag-writable yes --downstream-coupled yes
```

| 步骤 | 路径 | 判定 | 依据 |
|---|---|---|---|
| rag-00 | — | 部分生效 | 合成面识别到 RAG 组件；护栏资产未记录（如实标注，未断言无护栏） |
| rag-01 | A | 完全生效 | 恶意文档进入 top-3 |
| rag-02 | A | 完全生效 | 投毒后 top-k 改写；ASR（5 查询）= 0.80；碰撞相似度上界 0.7916 |
| rag-03 | B | 完全生效 | 载荷取自 top-1 检索片段原文 + 内嵌指令，下游回执执行 |
| rag-04 | C | 完全生效 | baseline vs manipulated 响应差异 |
| rag-05 | — | 已跳过 | `ai_vector.txt` 缺席，按「失败与豁免」跳过，不夸大 |

每步经 `collect_evidence.py --step rag-NN --strict` 收口（`EvidenceWriter.emit` 默认
`strict=True`），退出码 0；片段含确切命令 / 关键输出 / 截图三件套，并含
「证据校验（五件套 / 三件套）」表；rag-02/03/04 含 AI 交互日志段。

`rag-00` 给 `--recon-inventory loot/recon-ai.json` 时转为「完全生效」：组件、下游
agent 与护栏基线均由清单归类得出（见 `surface.py`）。

## 3. 可复现性

同一条命令在隔离 worktree 连续两次独立运行（不同输出目录），比对「关键输出」：
rag-00..rag-05 逐字一致 **6/6**（确定性 embedder 用 `zlib.crc32` 分桶，不受
`PYTHONHASHSEED` 影响；检索并列按 `doc_id` 升序）。

## 4. 反证（mutation）

对 `PoisonedRAGInjector.hit` 与 `DecisionDiff` 的差异判定各注入 `return False`：
`blackbox_enters_top_k`、`changed_when_context` 两用例转红；恢复后转绿，
且 `git diff` 对两文件为空（零残留）。

## 5. 门禁结论

B3 PASS（编译 + 89 测试）、B4 PASS（契约覆盖 6 步）、B5 PASS（flag 双通道 + 校验预言机
豁免通道）、B6 PASS（覆盖率 92.0% ≥ 80%）、B7 PASS（仅 `XPIATestWorkflow`，无
`orchestrator`）、B8 PASS（#145–#150 互链、双通道推送各试一次即停）。

## 6. SKILL.md 条款逐条对照（v1.1）

| # | SKILL.md 条款 | 实现 | 机器判据 | 结论 |
|---|---|---|---|---|
| 1 | 前置 1：复用 recon 清单确认 RAG 组件（向量库 / embedding / 检索接口 / 摄取通道） | `surface.from_inventory` 归类 `RAG库`/`向量库` 资产 | `test_identifies_components_and_downstream`、`test_rag00_with_inventory_is_fully_effective` | 通过 |
| 2 | 前置 2：识别消费检索结果的下游 agent 及其能力 | `RagSurface.downstream` / `capabilities`（未观测即「不可判定」） | 同上 | 通过 |
| 3 | 前置 3：记录护栏基线（检索过滤 / 输出审查 / 信任边界） | `RagSurface.guardrail_baseline()` | `test_missing_guardrails_are_explicit_not_assumed`、`test_guardrail_assets_become_baseline` | 通过 |
| 4 | 路径 A-1：经摄取通道或直接写入注入 | `ingest.HttpIngestChannel` / `FileIngestChannel` / `tools/inject_kb.py` | `IngestTests`（5 例）、`InjectKbCliTests`（3 例） | 通过 |
| 5 | 路径 A-2：高重叠文档 / embedding 对抗 / 直接操纵索引权重与元数据排序 | `PoisonedRAGInjector`、`EmbeddingCollisionCraft`、`IndexTamper` | `test_whitebox_asr_on_1k_corpus`、`IndexTamperTests`（5 例） | 通过 |
| 6 | 路径 A-3：取证恶意文档进入 top-k + 前后对照 | rag-01 / rag-02 关键输出 | 证据契约 `test_fragment_has_three_pieces_and_table` | 通过 |
| 7 | 路径 B-1：探针 before/after | `RetrievalProbe.before_after` | `test_before_after_fields_identical`、`test_no_injection_no_change` | 通过 |
| 8 | 路径 B-2：检索片段内嵌指令触发下游 | `build_payload(snippet=…)` + `run_xpia` | `test_xpia_payload_carries_retrieved_snippet` | 通过 |
| 9 | 路径 C：baseline vs manipulated 双次捕获 + AI 交互日志 | `DecisionDiff` + `ai_log` | `test_changed_when_context_manipulated`、契约 `test_llm_steps_have_ai_interaction_log` | 通过 |
| 10 | 收尾：`ai_vector.txt` 双通道一致 + `whoami/id` 访问证明 | `FlagProof.verify` + `--whoami` 实测值 | `test_flag_*`（4 例）、`test_flag_without_whoami_is_not_fabricated` | 通过 |
| 11 | 质量门：每步命令 / 输出 / 截图，统一经 `collect_evidence.py` | `evidence.EvidenceWriter`（`strict=True`） | 契约 10 例（三件套 / 五件套 / 严格模式退出码 1） | 通过 |
| 12 | 失败与豁免：只读 / 无写入通道 → 记录判定依据并降级 | `ReadOnlyChannel` + `rag-01` 分支 | `test_read_only_degrades_rag01`、`test_ingest_refused_is_not_effective` | 通过 |
| 13 | 失败与豁免：下游解耦 → 如实记「未产生影响」，评估改走 D3/D4 | `rag-04` 分支 | `test_coupled_no_records_no_impact` | 通过 |
| 14 | 失败与豁免：仅部分生效 → 记录效果等级 | 四值 `LEVELS`（完全/部分/未生效/已跳过） | `test_report_matches_fragments`、`rag-02` 分支 | 通过 |
| 15 | 校验标准：可 copy/paste 复现、与 report-exam 兼容、术语合规 | `_command()` 生成确切命令；片段结构由共享工具保证 | `test_full_run_with_recording_writer`、`check_glossary.py`、契约 `test_demo_step_ids_align_with_contract` | 通过 |

**未实现且如实标注的边界**：不直连 Milvus/Weaviate/Qdrant SDK（直写以 JSONL 语料
文件表达）；recon 清单无「下游能力」字段时记「不可判定」，不臆测。
