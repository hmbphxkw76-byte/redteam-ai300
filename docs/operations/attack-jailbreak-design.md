# attack-jailbreak — 模块与接口设计记录（阶段 6）

> 阶段 6 `codebase-design` 交付物 · 输入：规格 v2（#425）、工单（#426–#431）、调研 M1–M8
> 术语复用 `GLOSSARY.md` 既有条目（转换器/评分器/执行器/对象图），阶段 7 无新增术语需求 → GLOSSARY 不改动。

## 1. seam 清单（与阶段 2 核对结论一致）

| seam | 职责 | 输入 → 输出 | 错误行为 |
|---|---|---|---|
| `BackendFactory`（唯一真实 seam） | 承载全部 PyRIT 1.1.0 调用 | 步骤规格 + 目标 → 攻击结果 | PyRIT 缺失/调用失败抛注入异常 |
| `RealPyRITBackend` | 实现 BackendFactory，构造 1.1.0 对象图 | 同上 | 凭据缺失抛明确错误 |
| `FakePyRITBackend` | 同协议测试替身 | 同上 | 返回确定性假结果 |
| 证据适配器（复用） | `collect_evidence.py` 固定接口 | 步骤标识 + 产物 → 片段 | --strict 校验失败退出 1 |

新 seam 数量 = 0（BackendFactory 与证据接口均为既有成熟模式），符合 §3.6"新 seam 压到最少"。

## 2. 对象图（B7：全部 1.1.0 已核实）

- 执行器：`AttackExecutor(max_concurrency=1).execute_attack_async(attack=..., objectives=...)`（V4）
- 多轮策略：`RedTeamingAttack` / `CrescendoAttack` / `PAIRAttack` / `TreeOfAttacksWithPruningAttack`（M7）
- 目标：`OpenAIChatTarget`（V10）；评分：`SubStringScorer` 优先 + `SelfAskRefusalScorer` / `SelfAskLikertScorer`（V9）
- 转换器：`Base64Converter` / `LeetspeakConverter` / `ROT13Converter` / `TranslationConverter`（V6）
- 记忆：`SQLiteMemory` + `initialize_pyrit_async(memory_db_type="SQLite")`（V7/V8）
- 禁用：`pyrit.orchestrator` / `*Orchestrator` / `AzureOpenAIChatTarget` / 1.2.x 新增符号

## 3. 依赖方向（单向）

规格(#425) → 模块设计 → 实现(`tools/attack_jailbreak/`) → 测试(`tests/attack_jailbreak/`) → 证据(`collect_evidence.py`)。外部依赖仅经 seam 注入，测试替身可替换。

## 4. 被否决方案

- 否决"每策略一个 seam"：违反单一 seam 纪律，增加变更面。
- 否决"直接复制 handbook jailbreak/bypass.py"：其为 best-practices 字典 stub、无可执行引擎（评估结论）。
- 否决"升级到 1.2.x 用新符号"：违反版本锁定硬约束。

## 5. G0 门禁记录（阶段 5 / 6 / 7）

| 阶段 | 检查 | 依据 | 实测 | 结论 |
|---|---|---|---|---|
| 5 | 每张工单恰一个规范标签 | triage-labels | #427–#431 均 ready-for-agent | PASS |
| 5 | ready-for-agent 含 brief | §3.5 | body 含目标/验收/验证命令 | PASS |
| 5 | 阻塞边可查询 | #431 blockedBy=[430] | PASS |
| 6 | seam 数量与位置一致 | §1 | 新 seam=0，与阶段 2 一致 | PASS |
| 6 | 对象图无禁用名 | §2 | 全 1.1.0 类名 | PASS |
| 6 | 依赖方向单向 | §3 | 单向 | PASS |
| 7 | 术语映射覆盖 | 复用现有 | 转换器/评分器/执行器/对象图已存在 | PASS |
| 7 | check_glossary | B2 | 退出码 0 | PASS |
| 7 | B9 矩阵偏离关闭 | 矩阵 §1/§2 | 已补条目 17/18 | PASS |

阶段 5 / 6 / 7 结论：均 PASS（不符合项 0）。
