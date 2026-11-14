# attack-mcp-tool 术语映射表

> **版本** v1.0 · **输入** 规格 v2（#130）、`docs/operations/attack-mcp-tool-design.md`、`GLOSSARY.md`
> **性质** 阶段 7 交付物：SKILL.md 概念 ↔ 一手源概念 ↔ 实现标识符的双向映射，消除代码/规格/报告间的语义漂移

## 1. 映射表

| SKILL.md 概念 | 规范术语（GLOSSARY） | 一手源概念 | 实现标识符 | 定义要点 |
|---|---|---|---|---|
| MCP 端点 / 工具清单 | **工具面** | `tools/list` 的 `result.tools[]` | `ToolSurface`、`ToolDescriptor`、`JsonRpcMcpClient.list_tools` | 一次会话内可调用工具的集合及元信息 |
| 恶意 MCP server 投毒 | **工具投毒** | OWASP MCP Top 10 `MCP03:2025` | `poisoned_surface()`、`PoisonedMcpServer` | 篡改描述/注解/输出以改变调用决策 |
| 工具调用劫持 | **调用劫持** | OWASP MCP Top 10 `MCP06:2025` | `steps.PROMPT_INJECT`（伪造调用块）、`AgentSseClient.probe` | 以伪造调用或返回值替代真实链路 |
| 可信 / 可注入 server | **信任级别** | 目标侧 `mcp_telemetry.trust_level` | `ToolDescriptor.trust`、`model.parse_tool_entries` | `trusted`/`untrusted`/`shadow` |
| 权限边界 / 越权 | **越权调用**（沿用既有「权限提升」语义） | ASI02 / ASI03 | `model.has_admin_scope()`、`telemetry.permissions_used` | 以合法工具执行边界外动作 |
| 投毒生效判定 | **工具遥测** | 目标侧 `mcp_telemetry` | `Signals`、`grade()` | 确定性评分信号来源 |
| flag 双通道（无文件时） | **校验预言机** | `POST /api/secrets/validate` | `AgentSseClient.validate()`、`runner._probe_flag_file()` | 标识 + 答案的在线真值判定 |
| 每步证据 | **证据片段** | `tools/collect_evidence.py` 产物 | `evidence.EvidenceWriter.emit()` | 命令 + 输出 + 截图（+ 日志 + flag） |
| 效果等级 | **效果等级**（本文件定义，见 §2） | — | `grade.LEVELS`：完全生效/部分生效/未生效/已跳过 | 四值互斥，须附依据 |

## 2. 需在实现层固定的两条口径

1. **效果等级**不是 SKILL.md 的原生术语，是本实现引入的判定口径。四值语义见规格 v2 AC-08；报告中引用时须同时给出依据，禁止只写等级。
2. **校验预言机**只在目标不存在 flag 文件时启用；其「提交成功」不得被表述为「取得 `ai_vector.txt`」，二者在报告中必须区分措辞。

## 3. ADR 影响

| ADR | 是否需重开 | 说明 |
|---|---|---|
| ADR-0004（PyRIT 锁定） | 否 | 对象图基准不变；本技能仅声明式记录 `HTTPTarget` + `SubStringScorer` |
| ADR-0005（token 预算） | 否 | 产物遵循 C1–C8 |
| 新增 ADR | 不需要 | 无架构级不可逆决策 |

## 4. 门禁记录（阶段 7 / G0）

| 编号 | 检查项 | 依据 | 实测结果 | 判定 |
|---|---|---|---|---|
| B1 | 技能解剖结构 | `python scripts/validate_skill.py` | `PASS：共校验 16 个技能` | 符合 |
| B2 | 术语与决策一致 | `python scripts/check_glossary.py` | `PASS：检查 36 个废弃术语`（新增 6 条术语 0 冲突） | 符合 |
| B8 | 可追溯性 | 人工判据：§1 每条含一手源概念与实现标识符 | 9/9 映射完整 | 符合 |
| 验收① | 映射表覆盖规格与设计中的全部新概念 | §1 | 9 条覆盖（工具面/投毒/劫持/信任/越权/遥测/预言机/证据/等级） | 符合 |
| 验收② | GLOSSARY 条目含定义与来源 | `GLOSSARY.md` 攻击面节 | 6 条新条目均含定义；4 条附官方来源（MCP 规范 / OWASP MCP Top 10） | 符合 |
| 验收③ | `check_glossary.py` 通过 | 实跑 | PASS（36 项） | 符合 |
| 验收④ | ADR 编号连续、冲突显式标注 | §3 | 无新增 ADR；无冲突 | 符合 |

**结论：PASS**。不符合项 0。上游复核：`validate_skill` + `check_glossary` 通过；规格 v2 与设计文档未被改动。
