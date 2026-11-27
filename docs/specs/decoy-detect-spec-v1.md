# decoy-detect 行为规格 v1

> 回溯整理：依据 `skills/decoy-detect/SKILL.md` 与既有实现、测试归纳；**不代表原流程按序执行**。
> 整理日期：2026-11-27　状态：定稿（v1）

## 1. 背景与目标

exam 环境固定存在 2 台诱饵机（0 分，见 `GLOSSARY.md#诱饵机`）。对其投入攻击会空耗时间、拉低通过率。本技能覆盖 D2（诱饵机识别），以 ≤30min 时间盒对每台主机做三维度判定，主动放弃诱饵与信息不足主机，并与 `threat-model`、`report-exam` 形成闭环。

目标（可判定）：

- 每台被排除主机都有结构化判定条目与放弃理由。
- 单台判定耗时不超时间盒；超时主机有「不确定-已放弃」记录。
- 最终诱饵集合与考试规模预期（≈2 台）对齐；偏离时告警，不强行凑数。

## 2. 使用者与触发场景

| 使用者 | 触发或用法 |
|---|---|
| 演练执行者 | 进入诱饵判定时间盒（§5.3），已具备 recon-ai 枚举结果与各主机探测反馈 |
| threat-model 编排者 | 需将诱饵机从优先级攻击图排除，或复核初筛结论 |
| report-exam 记录者 | 需直接引用判定清单作为报告中的诱饵记录 |

## 3. 输入

输入为一份 JSON（`--inventory`），顶层含 `expected_decoys`（默认 2）与非空 `hosts` 列表。每台主机字段：

| 字段 | 含义 | 缺省 |
|---|---|---|
| `host_id` / `target` | 主机标识 | `unknown` |
| `present_categories` | recon-ai 枚举到的 AI 面类别 | 空 |
| `decoy_suspected` / `decoy_reason` | recon-ai 单机初判及理由（复用信号） | 假 / 空 |
| `high_value_service` / `reachable_entry` / `exploitable_misconfig` | 漏洞缺失三项 | 真 |
| `banner_service_count` | 枚举观察到的 banner/服务数 | 1 |
| `info_sufficient` / `inventory_match` | 信息充分性 / 与资产清单相符 | 真 |
| `elapsed_seconds` | 上游已测耗时（秒） | 0 |
| `threat_model_decoy` / `cross_validated` | 交叉验证信号 | 假 |
| `screenshot` | 可选截图路径（证据用） | 空 |

缺省按「有 AI 面、有价值」保守处理，避免把信息缺失误判为诱饵。

## 4. 输出与产物

- 判定清单 markdown：列固定为 主机标识 / 命中维度 / 具体依据 / 放弃理由 / 时间戳 + 结论；结论仅「诱饵」或「不确定-已放弃」，计分目标不入清单。
- 全局对账段：判定诱饵数与 `expected_decoys` 比较，不一致给出告警。
- 可选证据片段：`--evidence-dir` 时逐条落盘，三件套格式由 `tools/collect_evidence.py` 定义。
- 机读摘要：`--json` 输出 decoy_count / uncertain_count / scored_count / expected_decoys / violations / passed / count_matches。
- 退出码：0 完成且质量门通过；1 质量门或证据违规；2 用法或输入错误。

## 5. 行为约束

1. 维度判定顺序固定：行为特征＝无 AI 基础设施面；漏洞缺失＝三项攻击面全缺；无价值＝0 banner，或信息不足，或与资产清单不符。
2. 命中 ≥2 维度判「诱饵」；仅 1 维度须交叉验证（显式 `cross_validated` 或 `threat_model_decoy`）方可判诱饵，否则「不确定-已放弃」；0 维度为计分目标。
3. 时间盒默认 1800s；`elapsed_seconds` 超盒即强制「不确定-已放弃」并标记。
4. 清单五字段不得缺失；单维度未验证不得排除；超盒未按「不确定-已放弃」处置即质量门违规。
5. 术语统一「诱饵机」，禁用 `_Avoid_` 词；本技能仅识别与判定，不含攻击利用。

## 6. 失败与豁免

- 信息不足：在时间盒内结束，记「不确定-已放弃」及理由，不在 0 分主机空耗。
- 三维度均不命中但 threat-model 标记疑似：以交叉验证为准，不武断放弃真目标。
- 诱饵数偏离预期：告警并复核枚举完整性与判定逻辑，不强行凑数。
- 输入不可读 / 非 JSON / 缺 `hosts`：报错并以退出码 2 结束，不产出半成品清单。

## 7. 不在范围

- 不执行任何攻击、利用、提权或横向移动。
- 不实现 recon-ai 的枚举与 `judge_decoy`（单一事实源，直接消费其产物）。
- 不重定义证据片段格式（委托 `collect_evidence.py`）。
- 不引入 PyRIT 或 LLM judge：判定为确定性规则。
- 不覆盖 threat-model 的攻击图编排与 report-exam 的报告排版。
