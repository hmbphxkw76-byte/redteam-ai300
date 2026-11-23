# attack-multimodal — PyRIT 1.1.0 多模态 target 一手源核实记录

> **类型**：research（阶段 1 交付物）· **对象**：`attack-multimodal` skill
> **版本锁定**：`pyrit==1.1.0` · **取证日期**：2026-11-23（GMT+8）
> **依据**：主线 §3.1、B7/B8/B9；AGENTS.md C6（已核实事实不重复检索）
> **单一事实源**：本文件自包含 PyRIT 1.1.0 多模态 target 的一手源核实结论（M1–M8）。越狱策略类名复用权威索引 `docs/research/pyrit-canonical-references.md`（本文件存在，C6 不重复检索）。与 jailbreak 共用 M 编号仅为跨文档对照，不形成文件依赖。

## 1. 取证方法

一手源为 PyRIT v1.1.0 官方文档站 `https://microsoft.github.io/PyRIT/1.1.0/api/pyrit-prompt-target`（本轮新增核实，关闭上游权威索引 §4 的"多模态 target 未登记"核实闸）。越狱策略类名复用上游 V2–V9，不重复检索（C6）。

## 2. 已核实结论（多模态 target）

| 编号 | 结论 | 一手来源 |
|---|---|---|
| M1 | 1.1.0 的 `pyrit.prompt_target` 共 23 个类 | API Reference v1.1.0 |
| M2 | `OpenAIChatTarget` 明确支持多模态 image/text 输入 + 文本输出（+ 可选音频输出 via `OpenAIChatAudioConfig`） | 同上，类描述原文 |
| M3 | 图像生成/编辑 target 为 `OpenAIImageTarget`（无 `DALL-E` 命名类） | 同上 |
| M4 | 视频 `OpenAIVideoTarget`（text-to-video / text+image-to-video / remix）；语音 `OpenAITTSTarget`；实时音视频 `RealtimeTarget` | 同上 |
| M5 | 浏览器类 `PlaywrightTarget` / `PlaywrightCopilotTarget` 接受 `image_path` 消息片 | 同上 |
| M6 | `HTTPXAPITarget` 支持文件上传，可从 `converted_value` 推断 `file_path`（配合转换器如 `PDFConverter`） | 同上 |
| M7 | 编排与评分：`AttackExecutor(max_concurrency=1)`、`SubStringScorer` 优先、`Base64Converter` 等（复用 V2–V9） | 权威索引 |
| M8 | 禁用 1.2.x 新增符号（`output_attack_async` 等）与 0.x 旧名 | 权威索引 |

## 3. 考试对齐（OSAI AI300）

- 计分：AI 向量机 75/100 主分面；报告门槛极严（三/五件套 + copy/paste 复现）。
- 场景：跨模态注入/隐写载体（图像上传、OCR、PDF/文件输入）。payload 层复用 `attack-rag` 的 `multimodal_camouflage` 原语（白底白字/PDF 元数据/图像 OCR），target 层用 M2/M5/M6 已核实类。
- 证据：每步经 `collect_evidence.py --step multimodal-NN --strict` 产出，满足三/五件套与 flag 双通道。

## 4. 框架选型合规（B9 偏离声明）

矩阵原 16 条无 multimodal 条目。按 §1.4④/B9/GOVERNANCE §8.3 显式声明：多模态属 AI 主分面、PyRIT 占优场景，以 1.1.0 多模态 target 为内核；阶段 7 补矩阵条目 18（与 PR #432 的矩阵补条目并行，合并时取并集）。

## 5. 待核实项（实现前核实闸）

| 编号 | 待核实项 | 取证方式 |
|---|---|---|
| Q1 | `OpenAIChatTarget` 多模态消息片（image_path / data:image）确切构造形状 | 阶段 8 在已安装 1.1.0 环境内省构造参数；不阻塞其余路径 |
| Q2 | `OpenAIImageTarget` / `OpenAIVideoTarget` 是否需专用 endpoint（考试内网可达性） | 阶段 8 查构造参数 + 环境实测；不可达记 UNDETERMINED |

## 6. G0 门禁（阶段 1）

| 检查 | 依据 | 结论 |
|---|---|---|
| B7/B8/B9 | 1.1.0 类名 / 一手源 / 偏离声明 | PASS |
| 验收①–⑤ | 来源/版本/路径映射/核实闸/落盘 | PASS |

**阶段 1 结论：PASS**（不符合项 0；B9 偏离已显式声明）。
