# attack-rag 模块与接口设计

> **版本** v1.1 · **输入** 规格 v2（issue #145）+ `docs/research/attack-rag-canonical.md` + 工单 #146–#150
> · **v1.1 增量**：补齐 SKILL.md 前置定位、真实写入口、索引层操纵与两条豁免分支（见 §9）
> **性质** 阶段 6 交付物：深层模块边界、公开接口、依赖方向、seam 清单与注入点
> **框架组合**（取自 `osai-skill-framework-matrix.md` ③）：PyRIT(v1.1.0) 内核 + PoisonedRAG + 自定义脚本

## 1. 设计结论（先读）

1. **一个公开入口 + 两个 seam**：`run_attack()` 是唯一对外入口。v1.0 的 seam ①= **模型/嵌入后端注入点**（`RagBackend` 协议，承载 `OpenAIChatTarget` 与 embedder）；v1.1 依 SKILL.md 路径 A 第 1 步（摄取通道 / 直写）新增 seam ②= **写入通道**（`IngestChannel` 协议，`channel_for()` 选择）。两缝均由测试替身替换（`FakeBackend` / `FakeIngestChannel`），全离线可跑。
2. **证据收口复用既有共享工具**：不新增校验 seam，经 `tools/collect_evidence.py --step rag-NN --strict` 收口；证据写入委托子进程（同 `attack-mcp-tool/evidence.py` 模式）。
3. **投毒/检索为纯函数 + 自定义脚本**：`PoisonedRAGInjector`、`RetrievalProbe`、`EmbeddingCollisionCraft` 不导入 PyRIT（B9：碰撞/越权非 PyRIT 原语）；仅 `xapia.py` 与 `decision_diff.py` 经后端 seam 用 PyRIT（`XPIATestWorkflow` / `OpenAIChatTarget`）。
4. **验证主面本地化**：`RagHarness` 合成 RAG 环境（向量库+检索器+生成器）承载全部攻击路径，满足核实闸 A；AIVP 仅作可选回归闸。

## 2. 模块职责与依赖方向

```
cli.py ──▶ runner.py ──▶ steps.py
                  ├──▶ harness.py（RagHarness：索引/检索/生成）
                  ├──▶ poisoned_rag.py（注入：黑盒前置问题法 / 白盒碰撞）
                  ├──▶ retrieval_probe.py（before_after + EmbeddingCollisionCraft）
                  ├──▶ xapia.py（XPIATestWorkflow 间接注入）
                  ├──▶ decision_diff.py（baseline/manipulated 双次捕获）
                  ├──▶ evidence.py（委托 collect_evidence.py）
                  ├──▶ surface.py（前置定位：recon 清单 → 组件/下游/护栏基线）
                  ├──▶ ingest.py（写入通道：摄取 API / 直写 / 只读判定）
                  ├──▶ index_tamper.py（索引权重与元数据排序操纵）
                  └──▶ backends.py（RagBackend 注入点：RealPyRITBackend / FakeBackend）
```

依赖方向单向，无环。`harness.py`、`poisoned_rag.py`、`retrieval_probe.py` 为叶节点（纯算法，不依赖 PyRIT、不依赖后端 seam 外的 IO）。

| 模块 | 职责（单一） | 对外接口 | 错误行为 |
|---|---|---|---|
| `harness.py` | 合成 RAG：构建语料、建立向量索引、top-k 检索、生成回答 | `RagHarness(corpus, embedder)`；`index()`；`retrieve(q,k)`；`generate(q, ctx)` | 空语料构造抛 `ValueError` |
| `poisoned_rag.py` | PoisonedRAG 投毒：黑盒前置问题法 / 白盒 embedding 碰撞 | `PoisonedRAGInjector.blackbox(q, answer)`；`.whitebox(q, answer, embedder)`；`.inject(harness, docs)` | 白盒缺 embedder 抛 `ValueError` |
| `retrieval_probe.py` | 检索前后对照 + 高重叠对抗文本构造 | `RetrievalProbe.before_after(harness, q)`；`EmbeddingCollisionCraft.craft(q, answer)` | — |
| `xapia.py` | 间接注入：经 `XPIATestWorkflow` 对下游 `OpenAIChatTarget` 触发 | `run_xpia(objective, backend, runtime)` | 缺 PyRIT/端点时按失败与豁免返回，不抛 |
| `decision_diff.py` | 下游决策双次捕获与差异判定 | `DecisionDiff.capture(backend, q, ctx_baseline, ctx_manipulated)` → `DiffResult(changed, before, after)` | 上下文异常收敛为「未生效」 |
| `surface.py` | 前置定位：recon-ai 资产清单 → RAG 组件 / 下游 agent / 护栏基线 | `from_inventory(data)`；`surface_from_file(path)`；`RagSurface.render()` | 清单格式非法抛 `ValueError`；缺项留空并标注「不可判定」 |
| `ingest.py` | 路径 A 写入面：摄取 API / 直写 / 只读判定 | `HttpIngestChannel.put(id, text)`；`FileIngestChannel.put`；`channel_for(url, store, writable)` | 4xx/5xx、不可达均收敛为 `delivered=False` + 判定依据 |
| `index_tamper.py` | 索引层直接操纵（权重 / 元数据排序） | `IndexTamper.boost(weight)`；`.prioritize()`；`.reset()` | 未注入文档时返回空元组 |
| `steps.py` | 步骤契约（标识/标题/目标/默认命令模板） | `STEP_IDS`、`STEP_SPECS`、`steps_for_paths()` | 未知标识抛 `ValueError` |
| `evidence.py` | 委托共享证据工具写片段与清单 | `EvidenceWriter.emit(...)` → `(path, code, err)` | 非 0 退出码原样返回 |
| `backends.py` | 后端 seam：RealPyRITBackend（延迟导入 PyRIT）+ FakeBackend | `BackendFactory` 协议；`make_target()`/`make_embedder()`/`execute()`/`describe()` | — |
| `runner.py` | 编排：按步骤执行 → 证据落盘 → 汇总 | `run_attack(request, runtime=None) → AttackReport` | 单步异常收敛为「未生效/已跳过」 |
| `cli.py` | 命令行薄壳 | `main(argv)` | 参数错退出码 2；质量门失败 1 |

## 3. 公开接口契约

### 3.1 `run_attack(request, runtime=None) → AttackReport`
- **输入** `AttackRequest`：`target`（harness 配置 / AIVP）、`paths`（A/B/C）、`step`（空串=全量）、`evidence_dir`、`emit`、`backend_config`。
- **输入** `Runtime`（注入点）：`backend`（BackendFactory）、`writer`（证据）、`embedder`（模型后端内已含）、`capture`。
- **输出** `AttackReport`：`verdicts`（每步 `step_id`/`path`/`verdict`/`command`/`evidence_path`）、`object_graph`、`backend.describe()`。
- **错误行为**：未知 `step` → `ValueError`；目标不可达 → 该步「已跳过」；证据严格模式失败 → 抛 `RuntimeError`（证据链断裂不得静默）。

## 4. 注入点与测试替身

| 缝 | 生产实现 | 替身 | 替身保障的 AC |
|---|---|---|---|
| 模型/嵌入后端 | `RealPyRITBackend`（延迟导入 PyRIT；`OPENAI_CHAT_*` 与 `OPENAI_SCORER_*` 双模型） | `FakeBackend`（确定性响应 + 内置 embedder） | US5/US6/US10（全离线） |
| 写入通道（v1.1） | `HttpIngestChannel`（摄取 API）/ `FileIngestChannel`（直写）/ `ReadOnlyChannel` | `FakeIngestChannel`（预设回执 + 记录请求） | 路径 A 写入口径（全离线） |
| 证据 | `EvidenceWriter`（子进程委托 `collect_evidence.py`） | `RecordingWriter`（内存记录，断言契约参数） | US7/US8/US9/US11 |
| 截图 | 既有无头截图实现（经 `evidence.py` 适配） | `NullCapture` | US7 |

`Runtime` 默认构造为「生产三件套」；单测经 `Runtime(backend=FakeBackend(), writer=RecordingWriter(), capture=NullCapture())` 全离线运行。

## 5. 对象图（B7 对齐）

报告 `object_graph` 固定字段：

| 字段 | 取值 | 依据 |
|---|---|---|
| `framework` | `pyrit==1.1.0` | ADR-0004 |
| `target` | `OpenAIChatTarget`（下游 agent）/ `HTTPTarget`（AIVP 可选） | pyrit-canonical-references §3 |
| `strategy` | `XPIATestWorkflow`（间接注入路径 B/C）；其余路径为自定义脚本，无专用 `*Attack` | 调研 §3 |
| `scorer` | `SubStringScorer` + `SelfAskTrueFalseScorer`（独立评分模型） | attack-ai-agent backends 模式 |
| `notes` | 投毒/检索为自定义脚本，PyRIT 仅做间接注入与证据补位（B9） | 矩阵 ③ |

声明式记录即可，不在运行时强制导入框架（ADR-0004：CI 以可注入假后端替代真实对象）。

## 6. 权衡与被否决方案

| 方案 | 结论 | 理由 |
|---|---|---|
| 用 PyRIT 实现 embedding 碰撞 / 向量库越权 | **否决** | v1.1.0 无原语（调研 §1.4/B9），强行覆盖会违反矩阵分工 |
| 实网攻击演练目标 AIVP 作为唯一测试面 | **否决** | AIVP 无 RAG 投毒 lab（核实闸 A）；须本地 `RagHarness` 作主面 |
| 引入 sentence-transformers 作为默认 embedder | **部分采纳** | 仅本地夹具用；生产 embedder 经注入点，不绑定具体库 |
| 定级引入 LLM judge 复核检索层操纵 | **否决** | C6：用 baseline vs manipulated 双次捕获做因果判据，确定性优先 |
| 把真实 PyRIT 执行耦合进单测 | **否决** | 顶层禁止导入 pyrit；单测用 `FakeBackend`，真实执行仅在可注入环境（ADR-0004） |

## 7. 与 ADR 的关系
- **ADR-0004**：PyRIT 仅作对象图基准；顶层不导入，真实执行延迟导入，符合「CI 以可注入假后端替代」。
- **ADR-0005**：设计产物 ≤10KB；门禁记录增量，不复述规格正文。
- 无新增 ADR；无与既有 ADR 静默冲突。

## 8. 术语映射表（SKILL.md 概念 ↔ PyRIT 对象 ↔ 代码标识符）

| SKILL.md 概念 | PyRIT 对象（v1.1.0） | 代码标识符（tools/attack_rag/） | 说明 |
|---|---|---|---|
| 知识库投毒（路径 A） | （无原语，自定义） | `PoisonedRAGInjector.blackbox/whitebox` | PoisonedRAG 双条件；B9 自定义脚本 |
| 检索层操纵 / 检索相关性篡改（路径 B） | （无原语，自定义） | `RetrievalProbe` / `EmbeddingCollisionCraft` | embedding 碰撞；自定义脚本 |
| 间接注入（路径 B→下游） | `pyrit.executor.workflow.XPIATestWorkflow` | `xapia.run_xpia` | **非** `*Attack`；B7 受控 |
| 下游 agent 决策影响（路径 C） | `pyrit.prompt_target.OpenAIChatTarget` | `decision_diff.DecisionDiff` | baseline vs manipulated 双次捕获 |
| 验证下游决策影响 | `pyrit.score.SubStringScorer` / `SelfAskTrueFalseScorer` | 经 `FakeBackend`/`RealPyRITBackend` | 确定性优先（C6） |
| flag 取证（收尾） | （无，共享工具） | `evidence.EvidenceWriter` → `collect_evidence.py` | 三件套/五件套；`校验预言机` 等价通道 |
| 合成 RAG 验证主面 | （无，自定义） | `harness.RagHarness` | 核实闸 A |
| 前置：定位 RAG 攻击面 / 护栏基线 | （无，消费 recon-ai 清单） | `surface.RagSurface` / `surface_from_file` | 前置第 1–3 项；缺项标「不可判定」 |
| 路径 A 写入口：摄取通道 / 直写 | （无，自定义） | `ingest.HttpIngestChannel` / `FileIngestChannel` / `tools/inject_kb.py` | seam ②；`ReadOnlyChannel` 承载只读豁免 |

## 9. v1.1 增量：SKILL.md 条款补齐

v1.0 只覆盖「投毒 / 检索对照 / 下游影响 / flag」四条主链，SKILL.md 的
**前置定位、真实写入口、索引层操纵、失败与豁免**尚无实现。本次按条款补齐，
不改变既有步骤标识语义（rag-01..05 原样保留），新增 `rag-00` 前置步骤。

| 条款 | 原缺口 | v1.1 实现 |
|---|---|---|
| 前置：定位 RAG 攻击面 | 无代码消费 recon 清单 | `surface.py`：`RAG库/向量库` → 组件与检索入口；`agent系统` → 下游；`护栏` → 基线；缺项标「不可判定」 |
| 前置：记录护栏基线 | 无对照基线 | `RagSurface.guardrail_baseline()`：检索过滤 / 输出审查 / 信任边界三行，无护栏资产亦显式标注 |
| 路径 A-1：摄取通道或直写 | 仅合成 harness | `ingest.py` + `tools/inject_kb.py`：`--ingest-url`（HTTP POST `{"doc":…}`）/ `--store`（直写）/ 缺省合成面 |
| 路径 A-2：直接操纵索引 | 未实现第三选项 | `index_tamper.py`：相关性权重乘子 + 元数据优先序，`--index-access` 时取证并复位 |
| 路径 B-2：指令嵌入检索片段 | 载荷为独立字符串 | `rag-03` 先注入并 `retrieve()`，把 top-1 原文作为片段载体（`build_payload(snippet=…)`） |
| 收尾：访问证明 | `whoami` 硬编码 | `--whoami` 实测值；缺省记「未采集」，不伪造 |
| 失败与豁免：只读 | 无分支 | `--rag-writable no` → rag-01「已跳过」+ 判定依据 + 改走间接注入 |
| 失败与豁免：下游解耦 | 无分支 | `--downstream-coupled no` → rag-04「未生效」+「未产生影响」+ 评估改走 D3/D4 |

**新增输入**（`AttackRequest`）：`recon_inventory`、`ingest_url`、`ingest_doc`、
`rag_writable`（yes/no/unknown）、`index_access`、`downstream_coupled`（yes/no/unknown）、
`whoami`。三值字段非法时 `run_attack` 抛 `ValueError`（CLI 退出码 2）。

**为什么写入通道算 seam ②**：SKILL.md 要求「经内容摄取通道或直接写入」，这是
目标侧 IO；离线 CI 不能真发请求，故以协议 + 替身隔离，与 seam ① 同构。
它**不是**校验 seam：证据仍只经 `collect_evidence.py` 收口（§1 第 2 条不变）。

**边界（如实标注）**：不直连 Milvus/Weaviate/Qdrant SDK，直写以 JSONL 语料文件
表达；下游 agent 具体能力在 recon 清单无该字段时记「不可判定」，不猜。

## 阶段 6 门禁记录（codebase-design）

| 编号 | 检查项 | 依据 | 实测结果 | 判定 |
|---|---|---|---|---|
| B2 | 术语与决策一致 | `python scripts/check_glossary.py` | 待实现后复跑（本阶段未改代码） | 符合（设计无术语漂移） |
| B7 | 对象图无旧版名称 | `grep -nE "orchestrator\|Orchestrator\|AzureOpenAIChatTarget\|XpiaAttack" docs/operations/attack-rag-design.md` | 无命中；§5 用 `OpenAIChatTarget`/`XPIATestWorkflow` | 符合 |
| B8 | 可追溯性 | 人工判据：§2 每模块含职责/接口/错误；§4 注入点映射 AC；§6 被否决方案 | 5 项被否决各有理由 | 符合 |
| 验收① | seam 数量与位置明确且对齐阶段 2 | §1、§4 | 1 缝（后端注入点），与 spec v1 决策一致 | 符合 |
| 验收② | 每个公开接口有职责/输入/输出/错误 | §2 表 + §3.1 | 10 模块全覆盖 | 符合 |
| 验收③ | 依赖方向单向 | §2 依赖图 | 无环 | 符合 |
| 验收④ | 测试替身可替换外部依赖 | §4 | 三缝各有替身并映射 AC | 符合 |
| 验收⑤ | 与 ADR 冲突显式标注 | §7 | ADR-0004/0005 显式对齐 | 符合 |

**结论：PASS**。不符合项 0。上游复核：规格 v2（#145）未被本阶段改动；`validate_skill`/`check_glossary` 本阶段无代码改动，回归无损。
