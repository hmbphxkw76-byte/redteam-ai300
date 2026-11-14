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
