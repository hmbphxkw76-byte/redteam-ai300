# attack-ai-agent PyRIT 实现 · 变更清单与门禁记录

> **对象**：issue #83 规格 v2 / 工单 #105–#109 · **阶段**：8 `implement-spec`
> **版本**：`pyrit==1.1.0` · **一手源**：`docs/research/pyrit-v110-api-verification.md`
> **设计**：issue #83「设计记录 (codebase-design)」方案 A（单缝 + 深层模块）

## 1. 变更清单与工单对应

| 文件 | 职责 | 对应工单 |
|---|---|---|
| `tools/attack_ai_agent/__init__.py` | 唯一公开入口导出 | #105 |
| `tools/attack_ai_agent/steps.py` | 稳定步骤标识 `aia-01..12` 与 copy/paste 命令 | #109 |
| `tools/attack_ai_agent/paths.py` | 三路径对象图规格（`ComponentSpec` / `PathSpec`） | #106 / #107 / #108 |
| `tools/attack_ai_agent/backends.py` | `BackendFactory` 协议 + Real / Fake 双 adapter | #105 |
| `tools/attack_ai_agent/runner.py` | `run_attack` 编排、效果分级、证据发送 | #105 / #109 |
| `tools/attack_ai_agent/demo.py` | 端到端演示 CLI | #109 |
| `tests/test_attack_ai_agent_evidence_contract.py` | S2 证据契约夹具（7 用例：12 标识 1:1、三件套、flag 双通道） | #109 |
| `tests/test_attack_ai_agent_runner.py` | 单缝外部行为夹具（13 用例：四组响应、效果分级、失败与豁免、延迟导入） | #105 / #109 |
| `requirements.txt` | 依赖登记 `pyrit==1.1.0` + 测试框架（标准库 unittest） | #105 |
| `.github/workflows/ci.yml` | S1 `py_compile` 纳入新模块（AC-24/26） | #105 |
| `.gitignore` | 忽略运行时证据片段 `evidence/` | #109 |
| `evidence/attack-ai-agent/aia-01..12.md` | 12 份证据片段（运行时生成，经 `demo.py` 可复现；含时间戳，按 `.gitignore` 不入库） | #109 |
| `GLOSSARY.md` / `docs/governance/adr/0004-pin-pyrit-1.1.0.md` | 上游复核修正（含 XPIA 工作流术语、移除已排除名） | 阶段 1/7 |

## 2. 实现与规格对应矩阵（AC-01..AC-30）

| AC | 实现位置 | 验证方式 |
|---|---|---|
| AC-01 / AC-22 | 全包；`requirements.txt` | 静态检索无 0.x 名称；依赖登记 |
| AC-02 / AC-13 | `paths.py` `build_path_a` / `backends.py` `RealPyRITBackend` | 对象图含 `PromptSendingAttack` + `AttackExecutor.execute_attack_async` |
| AC-03 | `paths.py` B7 受控例外声明 | `XPIATestWorkflow` 归属 `pyrit.executor.workflow` |
| AC-04 | `paths.py` 路径 A 转换器构件 | `AttackConverterConfig` + `ConverterConfiguration.from_converters` |
| AC-05 / AC-06 | `paths.py` 评分器构件 | `SelfAskTrueFalseScorer` 线索 + `SubStringScorer` 决定性 |
| AC-07 / AC-08 | `paths.py` 路径 B 对象图 | `RedTeamingAttack(max_turns)` + `SQLiteMemory` / `memory_db_type="SQLite"` |
| AC-09 / AC-10 | `paths.py` 路径 B 召回与导出 | `PrettyAttackResultMemoryPrinter.write_async` |
| AC-11 / AC-12 | `paths.py` 路径 C 对象图 | `HTTPTarget` + 回调；与 D7 衔接点标注 |
| AC-14 / AC-17 | `runner.py` `emit_evidence` + `steps.py` | 每步 1:1 `--step aia-NN --strict`，标识集合 12 个 |
| AC-15 / AC-16 / AC-20 | `runner.py` `build_ai_log` / `flag_payload` | AI 交互日志、flag 双通道、访问证明 |
| AC-18 / AC-19 | `backends.py` 失败与豁免 + `runner.py` `grade` | 跳过依据与三级效果分级的确定性纯函数 |
| AC-21 / AC-24 / AC-25 / AC-26 | CI S1/S2 + `requirements.txt` | 校验器、编译、零依赖测试 |
| AC-23 | 顶层无 pyrit 导入；`RealPyRITBackend` 方法体内延迟导入 | 未装 pyrit 环境 `import tools.attack_ai_agent` 成功 |
| AC-27 / AC-28 | `GLOSSARY.md` PyRIT 实现层小节；不改写 `SKILL.md` | `check_glossary` 通过 |
| AC-29 / AC-30 | 一手源核实记录 + `demo.py` | 核实闸 P1–P4；端到端演示 |

## 3. 阶段 8 G0 门禁记录

**交付物**：上表全部文件 + 12 份证据片段 + 本记录。

| 编号 | 检查项 | 依据 | 实测结果（命令 + 输出摘要） | 判定 | 不符合项描述 | 修正要求 | 复验结果 | 结论 |
|---|---|---|---|---|---|---|---|---|
| G8-01 | 每条 v2 验收条件有对应实现位置 | §3.8-① | §2 矩阵覆盖 AC-01..30 | 符合 | 无 | 无 | 符合 | PASS |
| G8-02 | `py_compile` 通过 | B3/AC-24 | `python -m py_compile tools/attack_ai_agent/*.py` 退出码 0 | 符合 | 无 | 无 | 符合 | PASS |
| G8-03 | 对象图符合 B7（无 0.x / 已排除名） | B7/AC-01/03 | 静态检索两轮均无命中；`XPIATestWorkflow` 例外已标注 | 符合 | 初轮 `backends.py` 禁止清单含完整旧名字面量 | 改为文档指针，不重复字面量 | 复验无命中 | PASS |
| G8-04 | 每步证据三件套齐全且可 copy/paste 复现 | B4/B5/AC-14/17 | 12 片段全部「三件套齐全：是」；命令含 `--step aia-NN --strict` | 符合 | 初轮命令含未加引号 `<AGENT_ENDPOINT>`，bash 会解析为重定向 | `steps.py` `_cmd()` 加双引号 | 复验命令可安全粘贴 | PASS |
| G8-05 | 无硬编码凭据 | §3.8-⑤ | 端点经 `target_config` 注入；`requirements.txt` 无密钥 | 符合 | 无 | 无 | 符合 | PASS |
| G8-06 | 变更清单与工单一一对应 | §3.8-⑥ | §1 表映射 #105–#109 | 符合 | 无 | 无 | 符合 | PASS |
| G8-07 | B1 技能解剖 | B1 | `validate_skill.py` → `PASS：共校验 16 个技能` | 符合 | 无 | 无 | 符合 | PASS |
| G8-08 | B2 术语一致 | B2 | `check_glossary.py` → `PASS（检查 18 个废弃术语）` | 符合 | 无 | 无 | 符合 | PASS |
| G8-09 | B3 既有测试不回归 | B3 | `unittest discover -s tests -q` → `Ran 48 tests OK`（原 28 + 新增 20 用例：证据契约 7 + 单缝外部行为 13） | 符合 | 无 | 无 | 符合 | PASS |
| G8-10 | B8 上游交付物未被破坏 | §2.3 | #83 v1/v2、GLOSSARY、ADR-0004 均保留并复核 | 符合 | 无 | 无 | 符合 | PASS |

**结论**：`PASS`（初轮 2 项不符合已修正并复验）。阶段 8 可交付阶段 9。

## 4. 阶段 9 `tdd` 红—绿—重构记录与 G0

**交付物**：`tests/test_attack_ai_agent_runner.py`（12 用例）、`tests/test_attack_ai_agent_evidence_contract.py`（7 用例）、`tests/test_attack_ai_agent_adapters.py`（14 用例）、`scripts/measure_coverage.py`（标准库行覆盖率，可复现门禁命令）。

### 红 → 绿 → 重构

| 轮次 | 动作 | 实测输出 |
|---|---|---|
| 红 | 先写 33 个用例；其中 `test_batch_objectives_are_all_executed`（AC-13）针对未实现的批量 objective | `TypeError: run_attack() got an unexpected keyword argument 'objectives'`，`FAILED (errors=1)` |
| 退回阶段 8 | 按 §3.9 修正 `runner.py`：新增 `objectives` 入参、`AttackReport.objectives`、批量响应聚合（决定性命中取全批交集，防夸大） | 阶段 8 门禁复跑：`py_compile OK` / `validate_skill PASS` / `check_glossary PASS` |
| 绿 | 复跑该用例 | `ok`，`Ran 1 test ... OK` |
| 重构 | 消除夹具中 5 处未关闭文件的 `ResourceWarning`；新增适配器测试覆盖真实证据落盘与延迟导入分支 | 全量 `Ran 62 tests ... OK`，无 ResourceWarning |

### 覆盖率（标准库 `sys.settrace` + `code.co_lines()`）

`python scripts/measure_coverage.py --min 80` → 34 用例、`runner.py 97.7%` / `backends.py 88.1%` / `paths.py 99.2%` / `steps.py 98.3%`，**总计 449/469 = 95.7%**，高于 CI-CD §3 S2 的 80% 门槛。测量脚本在追踪窗口内重载模块，消除「导入早于 settrace」的假阴性；`co_lines()` 取 `lineno` 而非字节码偏移，消除测量假象。

| 编号 | 检查项 | 依据 | 实测结果 | 判定 | 不符合项描述 | 修正要求 | 复验结果 | 结论 |
|---|---|---|---|---|---|---|---|---|
| G9-01 | 每条验收条件有对应测试 | §3.9-① | 33 用例覆盖 AC-01..30 判据与 §2 矩阵 | 符合 | 无 | 无 | 符合 | PASS |
| G9-02 | 红阶段有实际失败输出留痕 | §3.9-② | 上表红轮 `TypeError` + `FAILED (errors=1)` | 符合 | 无 | 无 | 符合 | PASS |
| G9-03 | 全量 unittest 通过 | B3/§3.9-③ | `Ran 62 tests ... OK` | 符合 | 无 | 无 | 符合 | PASS |
| G9-04 | 覆盖率 ≥80% | B6/§3.9-④ | `python scripts/measure_coverage.py --min 80` → 95.7%，退出码 0 | 符合 | 初轮 42.4%（真实证据路径与延迟导入适配器未覆盖） | 新增 14 个适配器/落盘用例 + 追踪内重载 | 95.7% | PASS |
| G9-05 | 只测外部行为 | §3.9-⑤ | 行为用例只经 `run_attack`；适配器用例仅验命名空间与契约 | 符合 | 无 | 无 | 符合 | PASS |
| G9-06 | 本地与 CI 判定一致 | B6/§3.9-⑥ | CI S1/S2 命令与本地一致；CI 不安装 pyrit | 符合 | 无 | 无 | 符合 | PASS |
| G9-07 | 证据契约夹具断言每步契约 | B4 | 夹具断言 12 个标识各恰一次声明、三件套、AI 日志、flag 双通道 | 符合 | 无 | 无 | 符合 | PASS |
| G9-08 | 上游复核 | §2.3 | `validate_skill` 16 技能 PASS；`check_glossary` 18 废弃术语 PASS；12 份证据片段三件套齐全 | 符合 | 无 | 无 | 符合 | PASS |
| G9-09 | 门禁记录写入交付物并留 issue 摘要 | §2.2-5/B8 | 本节 + #83 评论摘要 | 符合 | 无 | 无 | 符合 | PASS |

**结论**：`PASS`。阶段 9 可交付阶段 10。

## 5. 阶段 10 `code-review` 双轴审查记录与 G0

**交付物**：本节记录 + #83 评论摘要。**审查范围**：`tools/attack_ai_agent/`（6 文件）、三个 S2 夹具、`scripts/measure_coverage.py`、CI 接线。

### 语义轴（实现 ↔ 规格 v2 一致性）

| 审查点 | 实测 |
|---|---|
| 单一公开 seam（方案 A） | `__init__.py` 仅导出 `run_attack` 等 API；对象图构造收敛于 `paths.py`（纯数据规格）/ `backends.py`（工厂），顶层零 pyrit 导入（AC-23 复验：未装 pyrit 环境导入成功） |
| 三路径对象图 | A=ASI01（`PromptSendingAttack`+`XPIATestWorkflow` B7 受控例外）；B=ASI06（`RedTeamingAttack(max_turns=5)`+`SQLiteMemory`/`memory_db_type="SQLite"`+`PrettyAttackResultMemoryPrinter.write_async`）；C=ASI02（`HTTPTarget`+回调，与 D7 仅标注衔接不实现）——与 §2 AC 矩阵逐条对应 |
| 证据契约 | `runner.emit_evidence` 每步 1:1 `--step aia-NN --strict`；flag 双通道含 `whoami/id` 访问证明（§6.2）；AI 交互日志四要素（§6.3） |
| 效果分级忠实 | `grade()` 纯函数：决定性命中→完全生效、仅 LLM 线索→部分生效、均无→未生效、能力缺失→已跳过并附依据；批量目标决定性命中取全批交集（防夸大，AC-19） |
| 失败与豁免 | `FakePyRITBackend` 无记忆/无工具分支返回「已跳过」+ skip_reason，不阻塞其余路径 |

### 工程轴（B1–B8 复核）

| 编号 | 检查项 | 依据 | 实测结果（命令 + 输出摘要） | 判定 | 不符合项描述 | 修正要求 | 复验结果 | 结论 |
|---|---|---|---|---|---|---|---|---|
| G10-01 | 实现与规格 v2 逐条对应 | §2 矩阵 | 语义轴表全部核对通过 | 符合 | 无 | 无 | 符合 | PASS |
| G10-02 | B7 静态检索无 0.x / 已排除名 | B7 | `grep -rnE "pyrit\.orchestrator|…Orchestrator|AzureOpenAIChatTarget" tools/attack_ai_agent/ tests/… scripts/…` → 实现代码零命中；唯一命中位于夹具自身否定断言清单（`test_no_legacy_api_names_in_implementation`，断言实现**不含**这些名） | 符合 | 无 | 无 | 符合 | PASS |
| G10-03 | B1/B2 技能解剖与术语 | B1/B2 | `validate_skill` → `PASS：共校验 16 个技能`；`check_glossary` → `PASS（检查 18 个废弃术语）` | 符合 | 无 | 无 | 符合 | PASS |
| G10-04 | B3 全量测试 + demo 冒烟 | B3 | `unittest discover -s tests` → `Ran 62 tests ... OK`；`python tools/attack_ai_agent/demo.py --step aia-02` → 步骤数 1、证据片段落盘 | 符合 | 无 | 无 | 符合 | PASS |
| G10-05 | B6 行覆盖率门禁 | B6 | `python scripts/measure_coverage.py --min 80` → 总计 95.7%（runner 97.7/backends 88.1/paths 99.2/steps 98.3），退出码 0 | 符合 | 无 | 无 | 符合 | PASS |
| G10-06 | AC-24 CI 接线 | AC-24 | `ci.yml` L30：`py_compile tools/collect_evidence.py tools/attack_ai_agent/*.py` | 符合 | 无 | 无 | 符合 | PASS |
| G10-07 | 证据片段不入库 | §3.8-⑤ | `git check-ignore evidence/attack-ai-agent/aia-02.md` 命中（按 `.gitignore` 忽略，运行时可复现） | 符合 | 无 | 无 | 符合 | PASS |
| G10-08 | B8 上游交付物未破坏 | §2.3 | `git diff main --name-status` 不含 `skills/attack-ai-agent/`（SKILL.md 未被改写）；#83 v1/v2、GLOSSARY、ADR-0004 保留 | 符合 | 无 | 无 | 符合 | PASS |

**建议级观察（不构成不符合项，不阻断）**：
- `RealPyRITBackend.execute` 为受控桩（RuntimeError 提示真实执行链需 `AttackExecutor` 与人工注入端点）——属阶段 8 最小切片声明范围，真实端点模式已由 triage 判为 ready-for-human，符合规格「CI 密闭 + 人工注入凭据」边界。
- `AttackRequest.step` 字段仅作公开 API 数据完整性保留，runner 内以局部 `step` 过滤——无行为偏差。

**结论**：`PASS`。阶段 10 可交付阶段 11（pr-push-review）。

## 6. 阶段 11 `pr-push-review` 记录与 G0

**交付物**：本节记录 + PR #110 + #83 评论摘要。复合阶段 = `pr`（PR 正文模板）+ `pre-push-review`（双轴语义评审与门禁复跑）+ 双通道推送与 PR 创建。

### pre-push-review（门禁复跑，单轮即绿）

| 编号 | 检查项 | 依据 | 实测结果（命令 + 输出摘要） | 判定 | 不符合项描述 | 修正要求 | 复验结果 | 结论 |
|---|---|---|---|---|---|---|---|---|
| G11-01 | B1 技能解剖 | B1 | `validate_skill` → `PASS：共校验 16 个技能` | 符合 | 无 | 无 | 符合 | PASS |
| G11-02 | B2 术语一致 | B2 | `check_glossary` → `PASS（检查 18 个废弃术语）` | 符合 | 无 | 无 | 符合 | PASS |
| G11-03 | B3 全量测试 | B3 | `unittest discover -s tests` → `Ran 62 tests ... OK` | 符合 | 无 | 无 | 符合 | PASS |
| G11-04 | B6 覆盖率 | B6 | `measure_coverage.py --min 80` → 95.7%，退出码 0 | 符合 | 无 | 无 | 符合 | PASS |
| G11-05 | py_compile（含新模块与测量脚本） | AC-24 | 退出码 0 | 符合 | 无 | 无 | 符合 | PASS |
| G11-06 | 语义复核 | §2 矩阵 | 单缝/对象图/证据契约/效果分级与阶段 10 语义轴一致，无新增偏差 | 符合 | 无 | 无 | 符合 | PASS |

### 推送与 PR

- 双通道推送：`git push origin feat/attack-ai-agent-stage9-11`（SSH）一轮成功，无需 origin-https 兜底。
- PR #110：正文按 PULL_REQUEST_TEMPLATE（变更摘要 / 纳管信息 D3·P0·AI向量机 / 实现要点 / 门禁记录 / 治理合规自检），`Closes #83 #105 #106 #107 #108 #109`。
- CI 复核以 PR 运行为准（S1 + S2 于 PR 触发；S3/S4 仅 main）。

**结论**：`PASS`。主线 11 阶段全部完成。
