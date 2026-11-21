# attack-rag Ch5 增量模块与接口设计

> **版本** v1.0 · **输入** 规格 v2（issue #274）+ 工单 #277–#283 + 调研 `docs/research/attack-rag-ch5-exploitation-canonical.md`
> **性质** 阶段 6 交付物：深层模块边界、公开接口、依赖方向、seam 清单
> **框架组合** 矩阵 ③（PyRIT v1.1.0 + PoisonedRAG + 自定义脚本）

## 1. 设计结论
1. **seam 不增加**：复用 v1.1 三个 seam（backend / ingest / evidence）；七个新模块均为纯函数或依赖既有 seam，无新外部 IO 边界。写入通道仍走 `ingest.py`。
2. **证据不新增校验 seam**：upload_manifest / trace_visibility 作为「关键输出」文本内容，经 `EvidenceWriter.emit()` 既有 `--output` 承载，collect_evidence 契约 v3 不变。
3. **对象图不变**：新攻击手法全为非 PyRIT 原语（编码/融合/探测/读文件/慢滴），按 B9 用自定义脚本；间接注入仍用 `XPIATestWorkflow`。

## 2. 模块职责与依赖方向

```
cli.py ─▶ runner.py ─▶ steps.py（新增 rag-06..rag-09 标识）
                  ├─▶ [既有] surface.py / ingest.py / poisoned_rag.py / retrieval_probe.py
                  ├─▶ capability.py（P0-1：能力探测 + 过滤不对称 + 休眠触发）
                  ├─▶ readchain.py（P0-1：读文件链 + 分批读取）
                  ├─▶ obfuscation.py（P0-3：编码/替换/同形/间接指令 + 多模态）
                  ├─▶ extract.py（P1-4：信息提取探针 + 多主题碰撞）
                  ├─▶ blend.py（P1-5：安全偏移 + 载荷预算 + citation 命名）
                  ├─▶ architecture.py（P2-6：检索模式/追踪字段归类）
                  ├─▶ slow_drip.py（P2-7：时间线 + 事件疲劳 + PDF 注记）
                  └─▶ evidence.py（委托 collect_evidence.py）
```

叶节点（纯算法、不依赖 PyRIT）：capability / readchain / obfuscation / extract / blend / architecture / slow_drip。依赖方向单向无环。

| 模块 | 单一职责 | 公开接口 | 错误行为 |
|---|---|---|---|
| `capability.py` | 4 类能力探测回执 + 过滤不对称结论 + 休眠文档构造 | `probe(capabilities)` → `ProbeResult`；`filter_asymmetry(direct_blocked, ctx_blocked)` → str；`dormant_doc(topic, instruction)` → str | 无能力输入返回「不可判定」渲染 |
| `readchain.py` | 文件读取链 UID 解析 + 分批读取 | `parse_uid(proc_status)` → str；`match_user(uid, passwd)` → str；`batch_lines(text, size)` → list[str] | 空文本返回空列表；无匹配记「不可判定」 |
| `obfuscation.py` | 编码/替换/同形/间接指令/多模态载荷 | `zero_widthify(s)`；`homoglyph(s)`；`indirect_instruction(s)`；`rotate(s,n)`；`multimodal_camouflage(kind)` → dict | 未知 kind 抛 ValueError |
| `extract.py` | KB 信息提取探针 + 多主题碰撞 | `probe_prompt(target)` → str；`one_shot(example)` → str；`multi_topic_collision(topics, payload, threshold=0.75)` → dict | 空 topics 抛 ValueError |
| `blend.py` | 融合安全区计算 + citation 命名 | `safe_offset(chunk, overlap, preview)` → int；`payload_budget(chunk, overlap)` → int；`citation_name(style, topic)` → str | 无 style 返回「不可判定」 |
| `architecture.py` | 检索模式 / 追踪字段归类 | `from_surface(surface)` → dict；`render()` → str | 缺字段标「不可判定」 |
| `slow_drip.py` | 慢滴时间线 + 事件疲劳 | `timeline(days)` → list[dict]；`event_fatigue(n)` → list[str]；`pdf_note()` → str | 未知 day 抛 ValueError |

## 3. 步骤标识扩展（ch5.py 独立契约）
新增 `rag-06`（能力探测与休眠触发，路径 B'）、`rag-07`（规避载荷构造，路径 B''）、`rag-08`（信息提取与多主题碰撞，路径 A'）、`rag-09`（文档融合与慢滴，路径 A''）。**设计修正**：这四步在 `tools/attack_rag/ch5.py` 以独立 `CH5_STEP_SPECS` 契约承载，不注入 `steps.py` 的 `STEP_IDS`；`rag-00..05` 语义与既有测试夹具原样保留，避免破坏主链证据契约。两组合计共用 `collect_evidence.py --step rag-NN --strict` 同一校验 seam。

## 4. 注入点与测试替身
沿用 v1.1：FakeBackend（离线响应 + embedder）、FakeIngestChannel（预设回执）、RecordingWriter（证据断言）、NullCapture。新模块无 IO，直接单测，无需替身。

## 5. 对象图（B7）
`framework=pyrit==1.1.0`；`strategy=XPIATestWorkflow`（仅路径 B 间接注入）；新手法为自定义脚本，声明于 `notes`，不引入 `*Attack` 误用。禁用名 grep 在阶段 10/11 复跑。

## 6. 权衡与被否决方案
| 方案 | 结论 | 理由 |
|---|---|---|
| 为 upload_manifest 新增 collect_evidence CLI 标志 | 否决 | 契约 v3 单一事实源；用既有 `--output` 承载即可，避免破坏 `collect_evidence.contract.md` 与 report_exam 解析 |
| 用 PyRIT 实现编码/融合/慢滴 | 否决 | v1.1.0 无原语（B9 + 矩阵 ③）；自定义脚本 |
| GLOSSARY 直接追加不腾空间 | 否决 | 现 17239 / 上限 17500，阶段 7 先合并近义条目 |
| 把 Phoenix trace 可见性写成"实测" | 否决 | 离线无法观测（V-3）；只写静态推断标注 |

## 7. 与 ADR 的关系
ADR-0004（PyRIT 声明式对象图）：符合；ADR-0006（三层隔离）：本 worktree + 单一共享文件并集；无新 ADR。

## 8. 门禁记录（阶段 6 / G0）
| 编号 | 检查项 | 依据 | 实测 | 判定 |
|---|---|---|---|---|
| B2 | 术语与决策一致 | check_glossary | 设计文档无废弃术语 | 符合 |
| B7 | 无旧版 PyRIT 名 | grep | 无命中 | 符合 |
| B8 | 可追溯 | §1–§6 | 每模块含职责/接口/错误 | 符合 |
| 验收① | seam 数量与阶段2一致 | §1 | 3 seam 不变 | 符合 |
| 验收② | 每接口有职责/输入/输出/错误 | §2 表 | 7 模块全覆盖 | 符合 |
| 验收③ | 依赖单向 | §2 图 | 无环 | 符合 |
| 验收④ | 替身可替换外部依赖 | §4 | 沿用三替身 | 符合 |
| 验收⑤ | ADR 冲突显式 | §7 | 无冲突 | 符合 |

**结论：PASS**。不符合项 0。
