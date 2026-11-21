# attack-rag Ch5 术语映射与建模决策

> **决策（显式，非静默偏离）**：本阶段**不增补 `GLOSSARY.md` 条目、不新增 ADR**。
> 依据：① ADR-0005 + `scripts/check_token_budget.py` 实测 GLOSSARY 17491/17500（LF 归一化，余量 9B），新增任一术语即超限；② ADR-0006：`GLOSSARY.md` 属并发会话共用长行，issue #275 并行会话正在处理 attack-embeddings 术语，本 worktree 不修改；③ 沿用 `docs/operations/capstone-rehearse-gate-stage7.md` 与 `capstone-rehearse-terms.md` 的既有先例——全部新概念归一到既有条目，用映射表覆盖规格与设计中的新概念。

## 1. 术语映射表（SKILL/Ch5 概念 ↔ GLOSSARY 既有条目 ↔ 代码标识符）

| 新概念（Ch5 锚点） | 归一到 GLOSSARY 既有条目 | 代码标识符 | 定义/来源 |
|---|---|---|---|
| Retrieval Hijacking / 上下文劫持（C-10..C-13） | `间接注入`（既有，GLOSSARY:71） | `capability.dormant_doc` | 把恶意指令置于被检索的可信上下文，绕过只作用于用户输入的过滤器（§5.2 行1041–1055） |
| 能力探测（C-11） | `AI 基础设施`（既有，GLOSSARY:144） | `capability.probe` | 探测命令/建文件/Web/读文件四类能力，回执可观察 |
| 过滤不对称（C-12） | `护栏`（既有；recon-ai 类别） | `capability.filter_asymmetry` | 输入过滤与检索上下文信任边界的差值；根因结论 |
| 读文件链 / UID 匹配（C-14） | `AI 向量机` 立足点取证 | `readchain.parse_uid/match_user` | 从 /proc/self/status 的 UID 反查 /etc/passwd 用户 |
| 零宽字符 / 同形字 / 替换 / 编码（C-18..C-20） | `间接注入`（既有）——属其载荷变形 | `obfuscation.zero_widthify/homoglyph/rotate` | 静态过滤绕过的表层编码，不改间接注入本质 |
| 多模态伪装（C-21） | `间接注入` + `AI 基础设施`（OCR 能力） | `obfuscation.multimodal_camouflage` | 图片 OCR / 白底白字 / PDF 元数据藏指令 |
| 信息提取探针 / one-shot（C-3） | `知识库内容提取`（既有，GLOSSARY:138 附近） | `extract.probe_prompt/one_shot` | 经对话探测提取主机/用户/凭据；与 `attack-embeddings` 向量直查互补 |
| 多主题碰撞（C-8/C-9） | `检索层操纵`（既有，GLOSSARY:69） | `extract.multi_topic_collision` | 单文档覆盖多主题形成多碰撞点，判据 >75% 响应命中 |
| 文档融合（C-22..C-24） | `知识库投毒`（既有，GLOSSARY:65）——属其隐蔽化变体 | `blend.safe_offset/payload_budget` | 按块/预览参数把指令藏在监控预览之外 |
| trace_visibility（V-3） | `证据`（既有证据契约术语） | `evidence` 关键输出字段 | 监控可见性判定；离线为静态推断，须实网复核 |
| 检索模式 / 追踪面（C-1/C-2） | `RAG`（既有，GLOSSARY:61）+ `AI 基础设施` | `architecture.from_surface` | 混合检索 BM25+向量、SHA-256 变更检测、分块、三元组存储、Phoenix |
| 慢滴投毒 / 提示分解 / 事件疲劳（C-25..C-27） | `知识库投毒`（既有）+ `间接注入`（提示分解属越狱策略） | `slow_drip.timeline/event_fatigue` | 跨天渐进改写 + 回退良性，规避版本比对 |

## 2. 定义与来源（供 code/review 消费）
- 所有新概念的定义与一手来源统一指向 `docs/research/attack-rag-ch5-exploitation-canonical.md`#2 的 C-1..C-29 锚点，不写入 GLOSSARY 正文。
- `_Avoid_` 禁用同义词沿用 GLOSSARY 既有条目登记的全部废弃表述，本文件不复述其字面以免触发术语检查器。
- 英文键名首次出现附中文括注（如 `trace_visibility`（监控可见性判定））。

## 3. 门禁记录（阶段 7 / G0）
| 编号 | 检查项 | 依据 | 实测 | 判定 | 结论 |
|---|---|---|---|---|---|
| B1 | 技能解剖结构 | validate_skill | 阶段 7 未改 SKILL.md（在阶段 8 改）| 符合 | — |
| B2 | 术语一致 | check_glossary | PASS（57 废弃术语） | 符合 | PASS |
| B8 | 可追溯 | §1 映射表 | 12 概念全映射既有条目 + 来源锚点 | 符合 | PASS |
| C4 | 产物预算 | check_token_budget | GLOSSARY 17491/17500 未改；本文件 2.1KB < 17KB | 符合 | PASS |
| 验收① | 映射表覆盖规格与设计新概念 | §1 | 12/12 | 符合 | PASS |
| 验收② | 条目含定义与来源 | §2 + 调研 C 锚点 | 全含 | 符合 | PASS |
| 验收③ | check_glossary 通过 | B2 | PASS | 符合 | PASS |
| 验收④ | ADR 冲突显式 | 头注 | 显式声明不增补理由 | 符合 | PASS |

**结论：PASS**。不符合项 0。显式偏离已声明（不增补 GLOSSARY / 不新增 ADR），理由见头注。
