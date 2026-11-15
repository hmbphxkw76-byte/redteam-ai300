# attack-rag 端到端验证（§8.1(d) / 阶段 9）

> **性质**：阶段 8–9 交付物的可复现验证证据；环境 Python 3.11、仅标准库、零网络。
> **被测**：`tools/attack_rag/`（12 模块）与 `tests/test_attack_rag{,_evidence_contract}.py`。
> **基线**：`origin/main@8aacd53`；实现恢复自归档 `e575290`（`wip/archive-orphans`）。

## 1. 语法、测试与覆盖率（B3 / B6）

```bash
python -m py_compile tools/attack_rag/*.py
python -m unittest tests.test_attack_rag tests.test_attack_rag_evidence_contract -q
python scripts/measure_coverage.py --target attack-rag --min 80
```

结果：编译无错；`Ran 51 tests ... OK`；行覆盖率 740/808 = **91.6%**（门槛 80%，exit 0）。
最低两模块为 `backends.py` 72.4%（真实 PyRIT 后端不可离线执行，按失败与豁免计）与
`cli.py` 75.8%（参数分支），其余均 ≥87%。

## 2. 五步证据链路（B4 / B5）

```bash
python tools/attack_rag/cli.py --path A --path B --path C \
  --evidence-dir <dir> --target rag-harness
```

| 步骤 | 路径 | 判定 | 依据 |
|---|---|---|---|
| rag-01 | A | 完全生效 | 恶意文档进入 top-3 |
| rag-02 | A | 完全生效 | 投毒后 top-k 改写；ASR（5 查询）= 0.80；碰撞相似度上界 0.7916 |
| rag-03 | B | 完全生效 | 下游执行检索片段内嵌指令（假后端回执） |
| rag-04 | C | 完全生效 | baseline vs manipulated 响应差异 |
| rag-05 | — | 已跳过 | `ai_vector.txt` 缺席，按「失败与豁免」跳过，不夸大 |

每步经 `collect_evidence.py --step rag-NN --strict` 收口（`EvidenceWriter.emit` 默认
`strict=True`），退出码 0；片段含确切命令 / 关键输出 / 截图三件套，并含
「证据校验（五件套 / 三件套）」表；rag-02 起含 AI 交互日志段。

## 3. 可复现性

同一命令在隔离 worktree 重跑，与主工作树早前独立运行（`evidence/attack-rag/`）比对：
rag-01..rag-05 的「关键输出」逐字一致 **5/5**（确定性 embedder 用 `zlib.crc32` 分桶，
不受 `PYTHONHASHSEED` 影响）。

## 4. 反证（mutation）

对 `PoisonedRAGInjector.hit` 与 `DecisionDiff` 的差异判定各注入 `return False`：
`blackbox_enters_top_k`、`changed_when_context` 两用例转红；恢复后转绿，
且 `git diff e575290 -- tools/attack_rag/poisoned_rag.py tools/attack_rag/decision_diff.py`
为空（零残留）。

## 5. 门禁结论

B3 PASS（编译 + 51 测试）、B4 PASS（契约覆盖 5 步）、B5 PASS（flag 双通道 + 校验预言机
豁免通道）、B6 PASS（覆盖率 91.6% ≥ 80%）、B7 PASS（仅 `XPIATestWorkflow`，无
`orchestrator`）、B8 PASS（#145–#150 互链、双通道推送各试一次即停）。
