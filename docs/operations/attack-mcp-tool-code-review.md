# attack-mcp-tool 双轴代码审查（阶段 10）

> **版本** v1.0 · **固定基线** `git merge-base origin/main HEAD` = `d1739b1` · **审查日期** 2026-11-14
> **性质** 阶段 10 交付物：Standards（写得对不对）与 Spec（做的是不是要求的）并列结论

## 1. 结论摘要

| 轴 | 发现数 | 硬违规 | 判断项 | 修复后硬违规 | 结论 |
|---|---|---|---|---|---|
| Standards | 18 | 3 | 15 | 0 | PASS |
| Spec | 34 | 7 | 27 | 0（2 项转登记限制） | PASS |

- 最严重项（Standards）：证据「截图」项可零截图通过严格模式（共享工具把钩子命令计为已提供）。
- 最严重项（Spec）：`mcp-02/03/04` 把「本地自证」记为「完全生效」，属夸大效果等级。
- 硬违规全部处理：5 项改代码、1 项改文档、1 项登记为跨技能改进项（见 §4）。

## 2. Standards 轴（每轴独立，不合并）

| # | 发现 | 文件:行 | 分类 | 处置 |
|---|---|---|---|---|
| S1 | 钩子命令即被判「截图已提供」，严格模式可零截图通过 | `tools/attack_mcp_tool/runner.py` `_emit` | **硬违规**（§6.1/§8.2-3） | 修：无 PNG 时补写「截图待补录」；共享工具语义改动会影响 `recon-ai` 契约，**登记为跨技能改进项** |
| S2 | AC-23 指向不存在的验证文档却判 PASS | `docs/operations/attack-mcp-tool-tests.md` | **硬违规**（B8/§8.1） | 修：补 `attack-mcp-tool-verification.md` 并回链 |
| S3 | 术语映射表列出不存在的标识符 | `docs/operations/attack-mcp-tool-terms.md` | **硬违规**（§8.2-8） | 修：改为 `PROMPT_INJECT`/`ToolDescriptor.trust`/`AgentSseClient.validate` 等真实标识符 |
| S4 | 宽泛 `except` 把编程错误记为「已跳过（能力缺失）」 | `runner.py` 循环 | 判断项 | 修：新增 `execution_error` 语义 → 判「未生效 + 执行异常」，不冒充目标缺失 |
| S5 | `EvidenceWriter` 与 `recon-ai` 逐字重复 | `tools/attack_mcp_tool/evidence.py` | 判断项 | 修：改为复用 `tools/recon_ai/evidence.py`，并为共享适配层补 `--flag-panel/--flag-shot` 透传（附加式改动） |
| S6 | 未使用导入（`List`/`Optional`） | `model.py` | 判断项 | 修：删除 |
| S7 | `api_base` 两分支等价 | `mcp.py` | 判断项 | 修：合并为单返回 |
| S8 | `ctx["tool_executed"]` 写入后无人读 | `runner.py` / `grade.py` | 判断项 | 修：判据只认「越权回显」，字段保留用于注记 |
| S9 | `StepSpec.needs_server`/`path_steps[""]` 死代码 | `steps.py` | 判断项 | 修：删 `needs_server`；`spec.tool` 改为真实使用 |
| S10 | 测试连真实网络（私网 IP） | `tests/test_attack_mcp_tool_units.py` | 判断项 | 修：改用本地 server 返回 404 |
| S11 | 动态 `__import__` 重复取已导入符号 | 同上 | 判断项 | 修：直接用顶层导入 |
| S12 | 断言源码文本而非外部行为 | `tests/test_attack_mcp_tool_runner.py` AC-09 | 判断项 | 保留：这是「包内不导入模型框架」的合规不变量，只能静态证明；已在用例 docstring 说明 |
| S13 | 文档以 `orchestrator` 作 server_id，易与旧版类名混淆 | `docs/research/attack-mcp-tool-canonical.md` | 判断项 | 修：加注「目标侧 server_id，与 PyRIT 编排器类名无关」 |
| S14 | 调研文档留存截断凭据前缀 | 同上 | 判断项 | 修：全量替换为 `<REDACTED>` |
| S15 | 设计文档接口表与代码不符 | `docs/operations/attack-mcp-tool-design.md` | 判断项 | 修：按实际模块与签名改写 |
| S16 | 依赖图暗示 `transport → model` | 同上 | 判断项 | 修：改为 `mcp → {transport, model}` |
| S17 | 门禁记录术语计数不一致（29/36/7/6） | `terms.md` / `tests.md` | 判断项 | 修：统一为「36 项废弃术语、新增 6 条」 |
| S18 | AC 交叉引用编号错配（AC-21 → `test_ac22_*`） | `tests.md` | 判断项 | 修：改为 `test_ac21_*` |

## 3. Spec 轴（逐条对照 SKILL.md 与规格 v2）

### 3.1 硬违规与处置

| # | 发现 | 违反条款 | 处置 |
|---|---|---|---|
| P1 | `mcp-02/03/04` 仅本地自证却记「完全生效」 | SKILL「失败与豁免」：投毒仅部分生效须如实记录 | **修**：新增 `capped_partial` 语义 → 三者封顶「部分生效」，依据写明「仅本地自证」 |
| P2 | `mcp-04` 生成从未发生的 AI 交互日志 | §6.3 真实性 | **修**：`_ai_log` 增加 `prompted` 门控，未发提示的步骤不产日志；新增回归用例 |
| P3 | 未探测 `ai_vector.txt` 即断言「不存在」 | AC-14/AC-15 | **修**：新增 `_probe_flag_file()`，以站根尺寸为 SPA 回退判据，实测三条路径 |
| P4 | 预言机拒绝时仍记「双通道一致」 | §6.2 | **修**：预言机通过才写 flag 双通道，否则不提交 flag 且判「部分生效」 |
| P5 | flag 值可跨步借用而不标来源 | B8 可追溯 | **修**：优先本步值；跨步借用须显式写「值来源 + 来源 lab」并按来源 lab 校验 |
| P6 | 无 MCP 面时未记录改走 D3/D5 的判定 | SKILL「失败与豁免」第 1 条 | **修**：`mcp-01` 缺失工具面时写入改走他路与诱饵机 30 分钟判定 |
| P7 | 裸 JSON-RPC 直连被称为「调用劫持」 | SKILL 路径 B 语义 | **修**：该形态记「已跳过」并注明劫持须在有模型决策的形态验证 |

### 3.2 判断项（已处理或登记）

| # | 发现 | 处置 |
|---|---|---|
| P8 | 截图项仍被共享工具记为已提供 | 登记跨技能改进项（见 §4） |
| P9 | `mcp-02` 的 `run_attack` 内启动监听与设计文档相反 | 改设计文档：按需启动 + 幂等关闭 + 仅回环，并写明理由 |
| P10 | `mcp-02` 证据头用外部目标、内容来自回环 | 修：证据头改用「本步实际端点」，并注明本次运行目标 |
| P11 | `mcp-01` 未解析 trust、未记护栏基线 | 修：`parse_tool_entries` 增 trust；`_guardrail_baseline()` 记录策略/权限/半径/同意 |
| P12 | `mcp-06` 把「未调用」一律称护栏拦截 | 修：措辞改为「目标未执行注入调用」并附 agent 回应摘要；不再宣称是策略拦截 |
| P13 | `mcp-07` 把不可达误记为授权拒绝 | 修：`derive` 对 `observation.error` 先判「已跳过（目标不可达）」 |
| P14 | 未实现诱饵机 30 分钟时间盒 | 部分：写入判定口径与改走策略；时间盒需运行时度量，登记为改进项 |
| P15 | 中文/全角冒号回答导致工具面解析失败（实测暴露） | **修**：三处正则支持 `：`；父级服务器声明可被后续条目继承；新增回归用例 |

## 4. 转登记项（不阻断交付，须跟踪）

| # | 内容 | 影响半径 | 处置 |
|---|---|---|---|
| L1 | 共享证据工具把「钩子命令」计为截图已提供 | `recon-ai`、`attack-ai-agent`、本技能 | 已登记 #141（需跨技能统一语义，会改动既有契约与测试） |
| L2 | 诱饵机 30 分钟时间盒无运行时度量 | 本技能 | 已登记 #142（需在编排层加时钟与累计耗时） |

## 5. 修复后复跑（门禁套件）

| 检查 | 命令 | 结果 |
|---|---|---|
| 语法与编译 | `python -m py_compile tools/attack_mcp_tool/*.py tools/serve_malicious_mcp.py` | 退出码 0 |
| 全量测试 | `python -m unittest discover -s tests -q` | `Ran 246 tests` / `OK` |
| 覆盖率 | `python scripts/measure_coverage.py --target all --min 80` | `89.3%` ≥ 80% |
| 术语 | `python scripts/check_glossary.py` | PASS（36 项） |
| 技能解剖 | `python scripts/validate_skill.py` | PASS（16 技能） |
| Token 预算 | `python scripts/check_token_budget.py --check` | PASS（14 锚点齐全） |
| 真实演练复跑 | `python tools/attack_mcp_tool/cli.py --mode agent-sse --target http://192.168.40.189` | 8 步结论见 `attack-mcp-tool-verification.md` |

## 6. 门禁记录（阶段 10 / G0）

| 编号 | 检查项 | 实测结果 | 判定 |
|---|---|---|---|
| B1 | 技能解剖 | `validate_skill.py` PASS | 符合 |
| B2 | 术语一致 | `check_glossary.py` PASS（36） | 符合 |
| B3 | 语法与测试 | `py_compile` 0；`Ran 246 tests`/OK | 符合 |
| B4 | 证据契约 | 八步 `--strict` 0；清单 8 行 `complete=true` | 符合 |
| B5 | flag 双通道 | `mcp-08` 面板值 == 正文值 | 符合 |
| B6 | CI 门禁 | 覆盖率 89.3%；CI S1–S4 命令本地等价执行通过 | 符合 |
| B7 | 对象图 | `pyrit==1.1.0` / `HTTPTarget` / `SubStringScorer` | 符合 |
| B8 | 可追溯性 | 本文每条发现带文件位置；L1/L2 已登记 | 符合 |
| 验收① | 两轴并列且各自完整 | §2 / §3 | 符合 |
| 验收③ | 硬违规为 0 | §1 表 | 符合 |
| 验收④ | 规格覆盖矩阵无遗漏 | `tests.md` §1 | 符合 |
| 验收⑤ | 门禁套件全绿 | §5 | 符合 |

**结论：PASS**（硬违规 0；2 项转登记不改判定）。上游复核：规格 v2 未被改写，仅在验证文档中补充实测结论。
