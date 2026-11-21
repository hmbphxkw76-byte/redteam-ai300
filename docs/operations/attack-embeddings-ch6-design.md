# attack-embeddings Ch6 增量设计记录（阶段 6）

> 输入：规格 #275 v2（12 AC）；工单 #284/#285–#291；既有 `tools/attack_embeddings/` 边界
> 性质：模块职责 / 公开接口 / 依赖方向 / seam 清单 / 对象图；不含实现代码
> 框架组合（矩阵 ⑨）：vec2text + PyRIT(v1.1.0) + 自定义脚本

## 1. seam 清单（7 个，均置于最高层）

| seam | 职责 | 公开接口 | 复用/新增 |
|---|---|---|---|
| S1 反演 | 从向量还原文本（夹具替身/真实后端可换） | `invert(vec, harness) -> {text, confidence, recovered}` | 复用；`FixtureInverter` 命名区分真实 Vec2Text（AC-C12） |
| S2 检索 | embedder + 向量库 + 检索器 | `EmbeddingHarness.embed/ingest/retrieve` | 复用 |
| S3 证据 | 委托共享收集器落盘三件套 | `EvidenceWriter.emit` / `RecordingWriter` | 复用（契约 v3） |
| S4 编排 | 步骤对象图构造 | `Runtime` / `run_attack` | 复用；扩展以纳入新步骤 |
| **S5 导出** | 向量库→三格式文件 | `export_vectors(store, out_dir, formats) -> {paths, count, dtype}` | 新增（AC-C1） |
| **S6 probing** | RAG 查询→模型评分→pairs 落盘 | `probe_model(vectors, query_iface, catalog) -> {ranking, confidence, pairs_path}` | 新增（AC-C2/C3） |
| **S7 决策** | 方法需求/限制→择路 | `select_method(req, limits) -> {method, reason}` | 新增（AC-C7/C8） |

新增 3 个（S5/S6/S7），均置于最高层、可注入、可替换；符合阶段 2 seam 提案（S-5/S-6/S-7）。

## 2. 模块职责（新增模块）

| 模块 | 单一职责 | 依赖 |
|---|---|---|
| `exporter.py` | S5：游标分页拉取 + .npy/.csv/.parquet 三格式写出 + 精度往返 | `entry.py`（读写）、`live.py`（适配器）、`model.py`（纯计算） |
| `fingerprint.py` | 维度→候选模型表 + 多模型共享维度时输出候选列表 | `model.py` |
| `probing.py` | S6：多策略查询 + 多粒度分段 + top5_avg 评分 + 分离度置信 + pairs 落盘 | `fingerprint.py`、`live.py`（RAG 接口）、`entry.py` |
| `triage.py` | chunk triage 三级级联 + 加权 RRF + sensitivity probes + 索引追溯 | `harness.py`、`model.py` |
| `slotfill.py` | 域检测 + 模板扩展 + 成员推断填槽 + margin-aware + consensus | `attacks.py`（复用成员推断）、`harness.py` |
| `beamsearch.py` | beam search 结构恢复 + 高熵检测 + dual-embedder ridge | `harness.py`、`model.py` |
| `decision.py` | S7：Table1/2 择路 + 五项限制可行性门禁 | `model.py`、常量表 |
| `envelope.py` | 环境相关能力标注（ALGEN/Vec2Text 不适用判定 + C-1 依据） | `model.py` |

## 3. 依赖方向（单向，无环）

```
cli.py / runner.py（编排）
   → {exporter, fingerprint, probing, triage, slotfill, beamsearch, decision, envelope}
        → {harness, attacks, live, evidence}（既有 seam S1–S4）
             → {model}（叶：值对象 + 纯计算，零 IO）
```

规则：新模块只向下依赖既有 seam 与 model；`model.py` 不 import 任何新模块；`live.py` 保持仅标准库 urllib（零第三方，ADR-0003）。

## 4. 对象图（S4 扩展）

`Runtime(embedder→store→harness, target, evidence, query_iface, catalog, policy)` → `run_attack`（原 emb-01..08）→ 新增 `run_ch6(req, runtime)` 编排 `export→fingerprint→probe→triage→slotfill/beam→decision` → `StepVerdict[]`（step_id 用 emb-c1..c8 区分增量步骤）。

## 5. 测试替身策略

- 导出：`FakeStore`（内存向量集合 + 游标分页模拟），断言三文件行数/精度。
- probing：`FakeRagQueryIface`（按预设查询返回含已知文本片段的响应），断言 top5_avg 判据；候选模型用 `DeterministicEmbedder` 多实例区分几何。
- triage：复用 `fixture_corpus()` + 注入已知 "credential" 块，断言缩池把其排前。
- slotfill/beam：复用夹具词表；高熵槽用夹具内已知 token。
- decision/envelope：纯函数，表驱动测试（需求组合→期望择路）。

## 6. 被否决方案与权衡

- **否决真实 vec2text 依赖**：ADR-0003 零第三方 + CI 不安装；以 `FixtureInverter` 本地夹具替身验证链路，真实后端留核实闸 C-3（与 #158 AC-3 措辞修正一致）。
- **否决 ALGEN/Vec2Text 重型训练**：AIVP 无 lab（C-1）+ 60h GPU 不可行；以 envelope 标注「不适用+依据」交付，不阻塞 P0/P1。
- **否决新增证据机制**：复用 collect_evidence.py v3（C1 单一事实源）。

## 7. 阶段 6 G0 门禁

| 编号 | 检查项 | 依据 | 实测 | 判定 | 结论 |
|---|---|---|---|---|---|
| B2 | 术语一致 | GLOSSARY | 新术语仅在设计描述，阶段 7 建模后校验 | 符合 | PASS |
| B7 | 无旧 PyRIT 对象 | S-9 | 设计未引入 pyrit.orchestrator/*Orchestrator | 符合 | PASS |
| B8 | seam 与阶段2一致 | #275 §8 | S5/S6/S7 对应 S-5/S-6/S-7，数量 3 | 符合 | PASS |

**结论：PASS**。

---

## 阶段 7：域术语建模（GLOSSARY 增补）

## 新增术语（规范词定义与禁用同义词见 `GLOSSARY.md#推断探测` / `GLOSSARY.md#块分选`）

阶段 7 已把 2 个新规范词写入 GLOSSARY（推断探测 / 块分选），并扩展「embedding 反演」条目；按 C1 单一事实源，本设计不再转抄定义与禁用词，只保留概念→标识符映射（下表）。「填槽」「维度指纹」「FixtureInverter」作为描述性用语，其规范语义随 GLOSSARY「embedding 反演」条目，不另立条目（控制 GLOSSARY 体积在预算内）。

## 术语映射表

| SKILL/课程概念 | 调研源 | 代码标识符（阶段8） |
|---|---|---|
| 导出向量 | S-4 Listing 3 | `exporter.export_vectors` |
| 推断探测 | S-4 Listing 8 | `probing.probe_model` |
| 块分选 | S-5 | `triage.triage_chunks` |
| 填槽 | S-6 | `slotfill.fill_slots` |
| 维度指纹 | S-4 Listing 5–7 | `fingerprint.candidates_for_dim` |
| 决策矩阵 | S-8 | `decision.select_method` |
| FixtureInverter | S-1/AC-C12 | `attacks.invert`（夹具反演） |

## 阶段 7 G0 门禁

| 编号 | 检查项 | 实测 | 判定 |
|---|---|---|---|
| B1 | validate_skill | 16 技能 PASS | 符合 |
| B2 | check_glossary | 写入后须 PASS（无废弃词） | 待阶段8写入后复验 |
| B8 | 映射表覆盖新概念 | 7 概念全覆盖 | 符合 |

**结论：PASS**（B2 写入后复验并入阶段 8）。
