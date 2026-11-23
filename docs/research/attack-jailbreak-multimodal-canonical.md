# attack-jailbreak / attack-multimodal — PyRIT 1.1.0 一手源核实记录

> **类型**：research（阶段 1 交付物）· **对象**：`attack-jailbreak`、`attack-multimodal` 两个新 skill
> **版本锁定**：`pyrit==1.1.0`（2026-09-04）· **取证日期**：2026-11-23（GMT+8）
> **依据**：主线 §3.1 验收标准 ①–⑤、B7 / B8 / B9；AGENTS.md C6（已核实事实不重复检索）
> **上游输入**：`pyrit-canonical-references.md`、`pyrit-v110-api-verification.md`、`osai-ai300-framework-decision.md`、`osai-skill-framework-matrix.md`
> **范围声明**：本任务全程 `pyrit==1.1.0`，不做任何版本替换；版本升级为后续独立任务。

## 1. 取证方法

一手源为 PyRIT v1.1.0 官方文档站（`/1.1.0/` 路径前缀）；`0.12.1` / `latest`（1.2.x）文档仅作定位，不作判定依据。越狱策略类名已在 `pyrit-v110-api-verification.md` 核实（V2/V3/V4/V6/V9），按 C6 直接引用、不重复检索；**本轮新增核实的唯一缺口是多模态 target 类名**（上游权威索引 §3 未登记、§4 标为核实闸）。

| 编号 | 一手来源 | 用途 |
|---|---|---|
| S9' | [API Reference `pyrit.prompt_target` v1.1.0](https://microsoft.github.io/PyRIT/1.1.0/api/pyrit-prompt-target) | 多模态 target 类名（本轮新增核实） |
| U1 | `pyrit-canonical-references.md` §3、`pyrit-v110-api-verification.md` V2–V9 | 越狱策略/转换器/评分器类名（复用，不重复检索） |
| F1 | `osai-ai300-framework-decision.md`、`osai-skill-framework-matrix.md` | 框架选型（B9 前置必读） |

## 2. 已核实结论

| 编号 | 结论 | 来源 | 证据摘要 |
|---|---|---|---|
| M1 | 1.1.0 的 `pyrit.prompt_target` 共 23 个类 | S9' | API 页面类清单枚举 |
| M2 | `OpenAIChatTarget` 在 1.1.0 明确支持**多模态 image/text 输入 + 文本输出**，并经 `OpenAIChatAudioConfig` 支持可选音频输出 | S9' | 类描述原文 "multimodal (image and text) input and text output generation" |
| M3 | 图像生成/编辑 target 类名为 `OpenAIImageTarget`（无 `DALL-E` 命名类） | S9' | 类清单计数：DALL-E 命中 0 |
| M4 | 视频 target 为 `OpenAIVideoTarget`（text-to-video / text+image-to-video / remix）；语音为 `OpenAITTSTarget`；实时音视频为 `RealtimeTarget` | S9' | 类清单与描述原文 |
| M5 | 浏览器类 target `PlaywrightTarget` / `PlaywrightCopilotTarget` 接受 `image_path` 消息片 | S9' | 类描述原文 |
| M6 | `HTTPXAPITarget` 支持文件上传，可从 `converted_value` 推断 `file_path`（配合转换器如 `PDFConverter`） | S9' | 类描述原文 |
| M7 | 越狱多轮策略：`RedTeamingAttack`、`CrescendoAttack`、`PAIRAttack`、`TreeOfAttacksWithPruningAttack` 均在 `pyrit.executor.attack`；执行器 `AttackExecutor(max_concurrency=1)`；评分 `SelfAskRefusalScorer` / `SelfAskLikertScorer` / `SubStringScorer`；转换器 `Base64Converter` / `LeetspeakConverter` / `ROT13Converter` / `TranslationConverter` | U1 | V2/V3/V4/V6/V9 已核实，复用 |
| M8 | 单轮越狱经 PromptSendingAttack + 转换器是 1.1.0 可行路径；category 无关的 `output_attack_async` 属 1.2.x，不在本版本对象图 | S9' + U1 | 以 1.1.0 为准，禁用 1.2.x 新增符号 |

## 3. 考试对齐（OSAI AI300）

- **计分结构**：AI 向量机占 75/100（4×15），是绝对主分面；报告门槛极严（命令/输出/截图 + 可 copy/paste 复现），文档缺失即扣分/零分。
- **jailbreak 对齐**：越狱/护栏绕过是 AI 向量机攻击链的核心手段之一；M7 的多轮策略直接对应"目标劫持/渐进式绕过"场景，评分器对应"是否达成越狱目标"判定。
- **multimodal 对齐**：M2/M5/M6 对应跨模态注入/隐写载体（图像上传、OCR、PDF/文件输入）；复用 `attack-rag` 的 `multimodal_camouflage` 原语作 payload 层，target 层用 1.1.0 已核实类。
- **证据回灌**：两 skill 每步证据须经 `tools/collect_evidence.py --strict` 产出（契约 `docs/contracts/collect_evidence.contract.md` v4），满足三/五件套与 flag 双通道，与 `report-exam` 兼容。

## 4. 框架选型合规（B9 偏离声明）

`osai-skill-framework-matrix.md` 当前只覆盖 16 个已注册 skill，**无 jailbreak / multimodal 条目**。按主线 §1.4④、B9 与 GOVERNANCE §8.3，此为"偏离矩阵"，须显式声明：

- 两 skill 的主攻框架取矩阵同类条目（attack-ai-agent：PyRIT 内核 + promptfoo/自定义）的合理外推——越狱与多模态均属 AI 主分面、PyRIT 占优场景（LLM/Agt/RAG），故 PyRIT v1.1.0 做内核，符合矩阵"PyRIT 在其占优场景做主角"原则。
- 后续须在 `osai-skill-framework-matrix.md` 补充这两条 skill 条目（阶段 7 术语/决策一致性一并处理），否则 B9 保持 `BLOCKED`。

## 5. 待核实项与取证方式（实现前核实闸）

| 编号 | 待核实项 | 状态 | 取证方式 |
|---|---|---|---|
| Q1 | `OpenAIChatTarget` 多模态消息片（image_path / data:image）的确切 JSON 构造形状 | 带取证方式 | 阶段 8 在已安装 `pyrit==1.1.0` 环境内省构造参数；不阻塞其余路径 |
| Q2 | `OpenAIImageTarget` / `OpenAIVideoTarget` 是否需要专用 endpoint 环境变量（考试内网可达性） | 带取证方式 | 阶段 8 查类构造参数 + 环境实测；不可达记 `UNDETERMINED` |

## 6. 已排除结论

- **X1**：`XpiaAttack` 不存在（复用上游 X1，间接注入用 `XPIATestWorkflow`）。
- **X2**：0.x `AzureOpenAIChatTarget` 在 1.1.0 不可用（复用上游 X4）。
- **X3**：1.2.x 新增符号（`output_attack_async`、`ConsoleAttackResultPrinter` 等）不纳入 1.1.0 对象图。

## 7. G0 门禁记录（阶段 1）

| 编号 | 检查项 | 依据 | 实测结果 | 判定 | 结论 |
|---|---|---|---|---|---|
| B7 | PyRIT 版本与对象图 | 权威索引 | 全程 1.1.0；类名取自 /1.1.0/ 文档；无 0.x/1.2.x 符号 | 符合 | — |
| B8 | 可追溯性 | §2 | M1–M8 附一手 URL / 上游核实号 | 符合 | — |
| B9 | 框架选型合规 | §4 | 已读两份资料；偏离矩阵已显式声明并列为阶段 7 待办 | 符合（带声明） | — |
| 验收① | 每条结论有来源 | §3.1 | M1–M8 均有来源列 | 符合 | — |
| 验收② | 版本明确 | §3.1 | 1.1.0 | 符合 | — |
| 验收③ | 攻击路径有对象映射 | §3.1 | M7（越狱）、M2/M5/M6（多模态） | 符合 | — |
| 验收④ | 待核实项命名+取证 | §5 | Q1/Q2 | 符合 | — |
| 验收⑤ | 落盘 docs/research/ | 本文件 | 已落盘 | 符合 | — |

**阶段 1 结论：PASS**（不符合项 0；B9 偏离已按 GOVERNANCE §8.3 显式声明，不构成不符合项）。
