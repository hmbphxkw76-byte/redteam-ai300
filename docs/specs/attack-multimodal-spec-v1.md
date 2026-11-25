# [spec-v1] attack-multimodal — 跨模态注入与隐写载体（PyRIT 1.1.0 原生）

> 阶段 2 `to-spec` ① · 行为规格 v1（What）· 本 issue 为行为唯一来源
> 上游：调研 `docs/research/attack-multimodal-canonical.md`（M1–M8）
> 标签：ready-for-agent

## 1. Problem Statement

OSAI AI300 的 AI 向量机占 75/100。当前项目对跨模态攻击仅有 `attack-rag` 的 `multimodal_camouflage` 原语（图像 OCR/白底白字/PDF 元数据），无独立多模态 skill：无稳定步骤契约、无承载 1.1.0 多模态 target 的 seam、无跨模态证据回灌。面对接受图像/文件上传的多模态 AI 端点，缺少可复用、可复现的注入链，影响 attack 阶段覆盖。

## 2. Solution

定义独立 skill，把"跨模态注入"固化为可验证闭环：payload 层复用既有伪装原语，target 层用 1.1.0 已核实的多模态 target 类（图像/文件/浏览器），评分与证据复用统一工具。skill 只定义行为/证据/验收；实现经单一 seam 承载，测试经同协议替身保持零依赖。

## 3. User Stories（行为清单）

- US-01 我能枚举目标的多模态输入通道（图像上传/PDF/OCR/浏览器 UI）。
- US-02 我能判定目标是否接受 `image_path` 或文件输入作为消息片。
- US-03 我能用白底白字/PDF 元数据/图像 OCR 生成跨模态伪装载荷。
- US-04 我能经图像 target 发送伪装载荷并观测模型响应。
- US-05 我能经文件上传 target 发送含隐藏指令的文档并观测摄取结果。
- US-06 我能经浏览器 target 向 Web UI 注入 `image_path` 消息片。
- US-07 我能对载荷做编码/字符变换绕过关键词过滤（复用转换器）。
- US-08 我能以确定性评分判定跨模态注入是否生效；不确定时转 LLM 评分。
- US-09 我能记录每步确切命令、关键输出、截图三件套。
- US-10 我能记录 AI 交互日志四字段（prompt/模型/输出/采纳）。
- US-11 我能以 `multimodal-NN` 稳定步骤标识逐步 copy/paste 复现。
- US-12 我能把 flag 以面板提交值 + 截图/正文双通道一致回灌。
- US-13 我能对不可达的多模态 target（端点缺失）如实记 UNDETERMINED，不伪造输出。
- US-14 我能对部分生效的注入如实记录等级，不高估。
- US-15 我能在未装 PyRIT 的 CI 环境用替身验证全部外部行为。
- US-16 我能保证不删减 C8 不可豁免条款。

## 4. Implementation Decisions

- D1：单一真实 seam 承载全部 PyRIT 调用，替身注入保持零依赖（C6）。
- D2：对象图用 1.1.0 已核实多模态 target（M2/M5/M6），禁用 0.x/1.2.x 符号。
- D3：评分确定性优先、LLM 补充（C6）。
- D4：证据复用共享取证工具，步骤标识为稳定契约。
- D5：payload 层复用 `attack-rag` 的 `multimodal_camouflage` 原语，不重复实现伪装算法。
- seam 提案：唯一真实 seam = BackendFactory 下 RealPyRITBackend；替身 = FakePyRITBackend。**沿用 jailbreak 已与用户核对采纳的模式。**

## 5. Testing Decisions

- 只测外部行为：步骤标识、target 可达性、评分分级、证据字段、确定性输出。
- 替身验证不依赖 PyRIT 安装；真实 seam 以接口断言覆盖，不连真实目标。
- 参考测试：`tests/attack_jailbreak/`（同构 seam）。

## 6. Out of Scope

- 不做 PyRIT 版本升级（全程 1.1.0）。
- 不含 handbook 高风险代码（multimodal/inject.py 不可 import，排除）。
- 不含真实考试目标利用动作；演练/仿真性质。
- 不重复实现 attack-rag 已有伪装原语。

## 7. Further Notes

- 框架矩阵偏离：无 multimodal 条目，按 B9/§8.3 声明，阶段 7 补条目（与 PR #432 并行取并集）。
- 核实闸 Q1/Q2 见调研 §5，带取证方式、不阻塞。

## G0 收尾（阶段 2 · B1/B2/B8）

| 检查 | 依据 | 结论 |
|---|---|---|
| 七节齐全 / US 覆盖 / 无路径代码 / 术语 / seam 核对 / B8 | §2 | PASS |

阶段 2 结论：PASS（不符合项 0）。
---
