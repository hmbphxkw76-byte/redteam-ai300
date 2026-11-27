# recon-ai — 工程规格 v2（历史留痕回填）

> 回溯整理：依据 `skills/recon-ai/SKILL.md` 与既有实现、测试归纳；**不代表原流程按序执行**。
> 整理日期：2026-11-27　状态：定稿（v2）

## 1. v1→v2 差异清单

- D1：把「默认被动」改为可机读判据 AC-01/02（报告头 `profile` 与执行序列）。
- D2：把「记录生效分级」改为 AC-03 三键断言（`target`/`profile`/`timestamp`）。
- D3：把「不推断存在」改为 AC-04 三值枚举与 AC-06 条目数不增。
- D4：把「按资产ID复用」改为 AC-13/14 七字段与 JSON 可解析。
- D5：把「证据含来源」改为 AC-17 脚本小节两态（有脚本 / 未使用脚本）。
- D6：把「flag 分记」改为 AC-18/20 不一致即 strict 退出 1。
- D7：把「失败隔离」改为 AC-22 `failed_steps` 与最终退出码。
- D8：新增 AC-26..32，覆盖 A2A、影子端点、发现、自校验、Ch2、Ch6、Ch9。
- D9：新增测试决策与门禁映射，逐条指向真实模块与命令。
- D10：新增证据与可观测性、风险与待验证两节；v1 行为定义不变。

## 2. 验收条件（AC-01…AC-32，布尔）

| AC | 判据（为真即通过） | 测试模块 |
|---|---|---|
| AC-01 | 无 `--profile` 时 `profile: passive` 且不执行主动端口步骤 | `tests.recon_ai.test_recon_ai`（`test_ac01`） |
| AC-02 | `--profile active` 时仅执行定向端口步骤，端口数 ≤8 | `tests.recon_ai.test_recon_ai`（`test_ac02`） |
| AC-03 | 报告头含 `target`/`profile`/`timestamp` 且均非空 | `tests.recon_ai.test_recon_ai`（`test_ac03`） |
| AC-04 | 存在性只取三值；回退页为不存在，JSON 命中为存在，超时为不可判定 | `tests.recon_ai.test_recon_ai`（`test_ac04`）、`test_recon_ai_units` |
| AC-05 | 部署配置含模型名时，资产「产品/引擎」非空且含该名 | `tests.recon_ai.test_recon_ai`（`test_ac05`） |
| AC-06 | 模型目录命中回退页时，资产条目数不因该探针增加 | `tests.recon_ai.test_recon_ai`（`test_ac06`） |
| AC-07 | recon-02 记录聊天端点、SSE 事件类型与 `request_id` | `tests.recon_ai.test_recon_ai`（`test_ac07`） |
| AC-08 | 检索痕迹命中建 RAG 资产；未命中记不可判定 | `tests.recon_ai.test_recon_ai`（`test_ac08`） |
| AC-09 | 被动面无端口证据时 recon-04 记不可判定并保留片段 | `tests.recon_ai.test_recon_ai`（`test_ac09`） |
| AC-10 | 识别阶段化编排面时清单含 `phase` 值 | `tests.recon_ai.test_recon_ai`（`test_ac10`） |
| AC-11 | recon-06 记录校验端点的状态码与 body 失败语义 | `tests.recon_ai.test_recon_ai`（`test_ac11`） |
| AC-12 | 无害回显命中记放行，拒答记拒答，两态可分 | `tests.recon_ai.test_recon_ai`（`test_ac12`） |
| AC-13 | 每条资产七字段非空；任一缺失即退出码 1 | `tests.recon_ai.test_recon_ai`（`test_ac13`） |
| AC-14 | 同时产出 markdown 与 JSON，JSON 可 `json.load` | `tests.recon_ai.test_recon_ai`（`test_ac14`） |
| AC-15 | 产物不含 `Bearer ` 明文或长密钥串，凭证仅指纹 | `tests.recon_ai.test_recon_ai`（`test_ac15`） |
| AC-16 | 每步片段含「确切命令」「关键输出」「截图（访问证明）」 | `tests.recon_ai.test_recon_ai`（`test_ac16`）、`test_recon_evidence_contract` |
| AC-17 | 片段含「脚本 / PoC」；无脚本须显式声明，有脚本须含来源或哈希 | `tests.recon_ai.test_recon_ai`（`test_ac17`） |
| AC-18 | flag 两通道相同记一致；不同记不一致且 strict 失败 | `tests.recon_ai.test_recon_ai`（`test_ac18`） |
| AC-19 | `MANIFEST.jsonl` 每行含 `step_id/command/sha256/timestamp/profile/retention/pieces` | `tests.recon_ai.test_recon_ai`（`test_ac19`） |
| AC-20 | 缺件套或双通道不一致且 `--strict` 时退出码 1 | `tests.recon_ai.test_recon_ai`（`test_ac20`） |
| AC-21 | 零组件时 `decoy_suspected` 为真且含依据与时间盒 | `tests.recon_ai.test_recon_ai`（`test_ac21`） |
| AC-22 | 单面失败入 `failed_steps`，其余步骤仍产出，退出码可 0 | `tests.recon_ai.test_recon_ai`（`test_ac22`） |
| AC-23 | `py_compile` 通过；无第三方 import；对象图无禁用 PyRIT 名 | `tests.recon_ai.test_recon_ai`（`test_ac23`）、`scripts/check_tools_compile.py` |
| AC-24 | 对真实目标运行退出码 0，产出 ≥7 片段、清单与验证报告 | `tests.recon_ai.test_recon_ai_closed_loop`、`test_recon_ai_generic_targets` |
| AC-25 | S0 套件全绿：技能解剖、术语、预算、全量测试 | `scripts/validate_skill.py`、`check_glossary.py`、`check_token_budget.py` |
| AC-26 | A2A 命中补录 Card/OpenAPI/注册端点；404 或坏 JSON 记 `ABSENT`；不新增 step_id | `tests.recon_ai.test_recon_ai_a2a` |
| AC-27 | 影子端点取 OpenAPI 与前端字面量差集，按置信度记；不入七字段 | `tests.recon_ai.test_recon_ai_shadow` |
| AC-28 | 发现阶段识别应用族/基路径/版本，请求 ≤12 且只读；未知端点不猜路径 | `tests.recon_ai.test_recon_ai_discovery`、`test_recon_ai_generic_targets` |
| AC-29 | 自校验 C1–C9 只读产物；截图待补录使 C4 失败；结论不取模板常量 | `tests.recon_ai.test_recon_ai_verifier` |
| AC-30 | Ch2 旁路分析零网络、输出经 schema 校验、不改 C1–C9 | `tests.recon_ai.test_recon_ai_ch2` |
| AC-31 | Ch6 向量库 `emb_metadata` 可选、只读、维度不可得不猜 | `tests.recon_ai.test_recon_ai_ch6` |
| AC-32 | Ch9 C1 判定只读、不新增 step_id、凭据不落明文 | `tests.recon_ai.test_recon_ai_ch9`、`test_recon_ai_c1_hardening` |

## 3. 测试决策

- 只断言外部行为：CLI 退出码、报告头、落盘片段、清单字段、门禁结论。
- 传输 seam 注入 `FakeTransport`，全部判据离线可测；真实 `UrllibTransport` 仅冒烟。
- 证据与截图 seam 注入替身；无浏览器时不伪造 PNG，以「待补录」驱动 C4 失败。
- 负向夹具覆盖不可达、超时、回退页、空体、非 JSON、字段缺失、通道不一致。
- 测试按技能分组于 `tests/recon_ai/`（14 个模块）；`unittest discover` 当前 180 例 OK。
- 覆盖率由 `scripts/measure_coverage.py --target recon-ai` 采集，门槛 80%。
- CI 不连接真实目标、不读取真实凭据；端到端演示以脱敏留痕引用。

## 4. 门禁映射

| 验收范围 | 基线 | 命令 | 判定口径 |
|---|---|---|---|
| AC-01..12、AC-21..22 | B1/B3 | `python -m unittest tests.recon_ai.test_recon_ai -q` | 分级、三值、七类判据、诱饵与隔离 |
| AC-13..20 | B4/B5 | `python -m unittest tests.recon_ai.test_recon_ai tests.recon_ai.test_recon_evidence_contract -q` | 七字段、三件套、双通道、strict |
| AC-23、AC-25 | B3/B6/B8 | `python scripts/check_tools_compile.py`、`validate_skill.py`、`check_token_budget.py --check` | 编译、解剖、预算 |
| AC-24、AC-26..30 | B3/B4 | `python -m unittest discover -s tests/recon_ai -t . -q` | 闭环、A2A、影子、发现、自校验、Ch2 |
| AC-31、AC-32 | B3/B7 | `python -m unittest tests.recon_ai.test_recon_ai_ch6 tests.recon_ai.test_recon_ai_ch9 tests.recon_ai.test_recon_ai_c1_hardening -q` | 只读、无新 step_id、不猜维度 |
| 覆盖率 | B6 | `python scripts/measure_coverage.py --target recon-ai --min 80` | 当前 85.3%（2433/2851） |

## 5. 证据与可观测性

- 运行目录 `runs/<run_id>/` 独占：片段、截图、`MANIFEST.jsonl`、`run.json`、`verification.json`。
- 门禁结论由 `verification.json` 派生；缺片段、陈旧、缺节、清单漂移均使对应 C 项失败。
- 每步证据含命令、输出、截图、脚本说明、AI 交互与 flag 双通道，供报告与 CI 独立消费。
- 历史门禁索引见 issue #121 评论：1–8 PASS/0，9 tdd 187 例 / 91.1%，10 硬违规 3→0，11 PR #128。
- 当前树复跑：180 例 OK；覆盖率 85.3%（2433/2851）。两组数字并存，后者为本次实测。
- 不引入额外遥测；证据片段与 `MANIFEST.jsonl` 是唯一可观测载体。

## 6. 风险与待验证

- 历史 187 例 / 91.1% 与当前 180 例 / 85.3% 不可直接对齐：测试已由扁平 `tests/` 迁至 `tests/recon_ai/`（#268），用例数与统计口径变化。
- `check_glossary.py` 仓库级当前 FAIL 1 项（`docs/specs/osai-exam-orchestrator-spec-v1.md` 命中废弃术语），非本技能文本；recon-ai 范围 0 命中。
- Ch2/Ch6/Ch9/A2A 的部分事实来自特定演练目标，未在本次复跑中重验；规格只保留可泛化判据。
- 阶段 4/5 无独立「分派完成」记录：工单 #122–#127 仍为 OPEN，标签与 brief 可核，实施由 PR #128 承载。
- 截图依赖本机浏览器；CI 无 GUI 时以替身验证失败路径，不验证真实渲染质量。
- garak 未接入首扫（V4）仍为已知偏离，未在本规格关闭。
