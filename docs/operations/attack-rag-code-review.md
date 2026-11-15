# attack-rag 双轴代码审查（阶段 10）

> **固定点**：`origin/main@8aacd53`；**范围**：`feat/attack-rag` 的 25 文件（19 新增 + 6 既有修改）。
> **方式**：Standards 轴（仓库规范 / C1–C8 / seam）与 Spec 轴（v2 US1–US11）分别核对，逐项附证据。

## 轴一：Standards

| 检查项 | 结论 | 证据 |
|---|---|---|
| C1 单一事实源 | 符合 | 证据片段结构委托 `tools/collect_evidence.py`；概念映射见 design §8，未转抄正文 |
| C2 增量门禁 | 符合 | 本文件与 verification 只记变更项 + 复验命令 + 结论 |
| B7 PyRIT 对象图 | 符合 | 库模块无顶层 `import pyrit`（延迟导入）；对象图仅 `XPIATestWorkflow` + `OpenAIChatTarget`，无 `orchestrator` / `*Orchestrator` |
| 零网络、可离线 | 符合 | 库模块无 `requests` / `urllib.request` / `socket`；CLI 缺省 `fake` 后端 |
| seam 收敛 | 符合 | 单一后端 seam `backends.py`（Fake / Real）；embedder 经 `DeterministicEmbedder` 注入，无第二套校验 seam |
| 输出纪律 | 符合 | `print(` 仅出现于 `cli.py`；库模块返回结构化结果 |
| 覆盖率与 CI 注册 | 符合 | `measure_coverage.py` 新增 `attack-rag` target 并纳入 `all`；`ci.yml` py_compile 含 `tools/attack_rag/*.py` |

## 轴二：Spec（US1–US11）

| US | 验收条件 | 结论 | 证据 |
|---|---|---|---|
| US1 | top-k 返回且长度 ≤k | 通过 | `-k harness` |
| US2 | 黑盒注入后 top-k 含 `mal-*` | 通过 | `-k blackbox` |
| US3 | 5 篇注入 ≥1k 语料 ASR ≥0.5 | 通过 | ASR = 0.80（1200 语料） |
| US4 | before/after 两列表结构一致 | 通过 | `-k probe` |
| US5 | XPIA 经 `XPIATestWorkflow` 产出响应 | 通过 | 假后端回执含 `executed` / `response` |
| US6 | 上下文被操纵时 `changed is True` | 通过 | `-k decision`（含变异反证） |
| US7 | 每步 `--strict` 退出 0、三列齐全 | 通过 | 契约夹具 + 5 份片段 |
| US8 | 含 LLM 步骤有 AI 交互日志 | 通过 | rag-02 / 03 / 04 |
| US9 | flag 双通道一致；缺席走校验预言机 | 通过 | `FlagProof.verify()` + `FlagProof.oracle` 等价通道 |
| US10 | 编译 + 全绿 + 覆盖率 ≥80% | 通过 | 51 测试、91.6% |
| US11 | 「证据校验（五件套 / 三件套）」表对齐 `report-exam` | 通过 | 契约断言表头 |

## 发现与处置（3 项，均已修复）

1. 术语漂移：步骤契约已用「检索层操纵」，`SKILL.md` 与 `examples/evidence-demo.md` 仍为旧称，
   导致契约断言失败 → 统一 6 处，断言转绿。
2. 预算超限：GLOSSARY 增 4 条术语后实测 15412B，超 15000 上限 → 按 ADR-0005
   「基线 + 必要增量」上调至 16000（余约 588B），不删既有内容。
3. CI 注册缺失：`py_compile` 未含 `tools/attack_rag/*.py` → 已补，避免新模块绕过 S1。

硬违规 0；规格覆盖 11/11。
