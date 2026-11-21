# Ch4 A2A 对齐全量主线：阶段 1 调研记录

> 任务：对 `threat-model` / `recon-ai` / `attack-multi-agent` 做 Ch4 A2A 对齐式 re-landing。本文是阶段 1 一手源调研产物，供阶段 2/3 规格与阶段 6 设计引用。
> 调研日期：2026-11-21（GMT+8）。基线：`origin/main`，隔离 worktree `D:/_mainline-a2a-ch4_wt`，分支 `feat/a2a-ch4-mainline`。

## 1. 一手来源与版本锚点

| 来源 | 位置 / 版本 | 用途 |
|---|---|---|
| OffSec AI-300 Ch4 | `D:\视频\OffSec   AI-300 Advanced AI Red Teaming\Ch4-Attacking-MultiAgent-Systems-and-A2A-Protocol.html`，§4.1–§4.8、Table 1–3、Listing 1–66 | A2A 架构、枚举、利用、规避、验收的唯一教材源 |
| 主线规范 | `docs/operations/skill-mainline-workflow.md` v1.2，§1–§3 | 11 阶段、G0、B1–B9、T1–T6 |
| 框架决策 | `docs/research/osai-ai300-framework-decision.md`，§2/§4/§8 | best-of-breed 分层栈，PyRIT 为内核非唯一 |
| 框架矩阵 | `docs/research/osai-skill-framework-matrix.md`，§⑥/§⑩/§⑬ | 三技能强制组合 |
| 证据契约 | `docs/contracts/collect_evidence.contract.md` + `docs/contracts/consumers.md` | 三件套/五件套、flag 双通道、消费者边界 |
| 版本约束 | `docs/research/pyrit-canonical-references.md`；`pyrit==1.1.0` | B7 对象图与禁用旧名 |
| 治理 | `GOVERNANCE.md` §4.2/§4.4/§8.2；`AGENTS.md` C1–C8；ADR-0006 | 技能解剖、证据、隔离与预算 |

## 2. 已核实结论

1. **教材范围**：Ch4 由三个学习单元组成——Multi-Agent Architecture Overview、Enumerating A2A Workflows、Attacking A2A Workflows（§4 开篇；§4.1–§4.7）。§4.8 收束为“协议重互操作轻安全”，防御建议为双向 TLS、签名 Agent Card、认证注册、每个 agent 边界内容过滤。
2. **协调模式与风险**：编排器（单点故障）、点对点（信任传播）、层级（垂直提权/上级冒充）、流水线（载荷持久化与能力跳跃）均来自 §4.1 正文与 Figure 1–4；框架风险分别列出 LangGraph/AutoGen/CrewAI/OpenAI Swarm/Google A2A（§4.1）。
3. **信任与向量**：§4.1 明确 confused deputy、智能体间未验证输出、工具信任、系统信任三类边界；攻击向量按输入/处理/输出/持久化四类列举。
4. **A2A 枚举链**：§4.2 顺序为 SIEM 规则基线（Table 1）→ 端口发现（Listing 1）→ `/.well-known/agent.json` 逐端口枚举（Listing 2–6）→ 架构图（Figure 6）→ `/openapi.json` 路径与 `$ref` schema（Listing 7–9）→ 合法 `/a2a/workflow` 基线（Listing 10）。
5. **利用面**：§4.4 工作流绕过（增量信任/history 注入，Listing 11–13，成功判据为 `content_review` 缺席且 `security_report:null`）、PPTX 恶意链接与规避（Listing 14–18，Figure 7–8）、`xp_cmdshell` 盲命令与 ICMP 带外验证（Listing 20–22）、SQL 编码绕过（Listing 24）；§4.5 恶意 Agent 注册/隐蔽变体/注销（Listing 25–40）；§4.6 hosts/DNS 欺骗与响应格式 `state` 顶层+`result.parts`（Listing 41–50，Table 2）；§4.7 OpenAPI 可写端点→投毒→触发泄露（Listing 51–66，Table 3）。
6. **框架组合对齐**：矩阵 §⑩ 规定 `attack-multi-agent` = A2ASecBench + Cisco a2a-scanner + PyRIT `HTTPTarget`（非主演）+ A2A SDK；既有设计 `docs/operations/attack-multi-agent-design.md` 已声明 `scanner` seam 与 `pyrit_attack` 懒导入，组合一致。矩阵 §⑬ `threat-model` 为方法论 + 文档 + 许可 AI 助手，无专用框架。矩阵 §⑥ `recon-ai` 推荐 garak 首扫 + Kali 侦察 + 许可 AI 助手。
7. **契约基线**：`attack-multi-agent` 的 `a2a-01..a2a-08` 是 S2 机器判据，SKILL.md 必须恰好 8 个 `collect_evidence.py --step` 调用；`recon-ai` 为 `recon-01..recon-07`，七字段资产清单契约为下游复用边界；三者均不得使用 GLOSSARY `_Avoid_` 术语。
8. **三层隔离**：ADR-0006 与主线 §1.3(7) 要求独立 worktree/分支、推送前 `checkout_lock.py --check`、main 仅经 PR 合并；本任务已建 `D:/_mainline-a2a-ch4_wt` 与 `feat/a2a-ch4-mainline`。

## 3. 攻击路径 → 对象 / 步骤映射

| 技能 | Ch4 路径 | 现有契约 / seam | 本轮对齐动作 |
|---|---|---|---|
| threat-model | §4.1 四模式、框架风险、信任边界、四类向量 | 规划产物，无攻击对象 | 在信任边界节补标模式/风险/向量，质量门与豁免同步 |
| recon-ai | §4.2 Agent Card/OpenAPI/注册端点/SIEM 基线 | `recon-05`（agent 系统识别）、`recon-07`（护栏探测）；`transport`/`discovery` seam | 不新增 step_id；在 recon-05/07 证据片段补录协议字段与检测基线 |
| attack-multi-agent | §4.4–§4.7 六类 A2A 利用面 | `a2a-01..a2a-08`；`scanner` + `pyrit_attack` 懒导入 seam | 保持 8 步契约；用专项表补触发/命令/判据/异常，不新增 PoC 脚本 |

## 4. 待核实项（转核实闸）

| 编号 | 待核实 | 取证方式 | 阶段去处 |
|---|---|---|---|
| V1 | `/.well-known/agent.json` 是否纳入 `tools/recon_ai/probes.py` 的 `STEP_SPECS` | 在实现阶段决定最小 seam；若新增须回归 C1–C9 与七字段契约；否则留规格命令级并记后续工单 | 阶段 6/8/9 |
| V2 | rogue/spoof/poison 是否需要独立可执行 PoC 脚本 | 规格 v2 界定“命令级规格”与“脚本实现”边界；不默认扩张实现面 | 阶段 3/6 |
| V3 | 真实演练目标 192.168.50.25/131/132/133 与 SIEM 规则 | 人工核实闸：带 curl/tcpdump/PPTX 检查命令与原始字段判据；本地静态校验不得替代 | 阶段 3/9/11 |
| V4 | recon-ai 未实现 garak 首扫，与矩阵 §⑥ 存在偏离 | 显式声明：Ch4 A2A 发现是 HTTP 协议枚举，garak 面向模型层探针，加入会变成无关能力；按 GOVERNANCE §8.3 记录理由 | 阶段 2/3/10 |

## 5. 已排除

- 排除把单 agent 间接提示注入重新定义进 `attack-multi-agent`：已由 `attack-ai-agent` 路径 B 覆盖，仅交叉引用。
- 排除新增 skill：三技能已覆盖 D10/D2/D4，新增会破坏 GOVERNANCE §4.4 登记与 C4 预算。
- 排除在本次对齐中改 `tools/collect_evidence.py` 与 `GLOSSARY.md`：前者为共享契约、后者接近 17500B 上限，且 Ch4 术语已有规范词。

## 6. 阶段 1 G0 门禁记录

| 编号 | 检查项 | 依据 | 实测结果（命令 + 输出摘要） | 判定 | 不符合项描述 | 修正要求 | 复验结果 | 结论 |
|---|---|---|---|---|---|---|---|---|
| B7 | PyRIT 版本与对象图 | 主线 §2.1 B7 | `grep pyrit==` → `pyrit==1.1.0`；无 `pyrit.orchestrator` | 符合 | 无 | 无 | — | PASS |
| B8 | 可追溯性 | 主线 §2.1 B8 | 本文件 §1–§3 逐条附路径 / 章节 / Listing | 符合 | 无 | 无 | — | PASS |
| B9 | 框架选型合规 | 主线 §1.4/§2.1 B9 | 矩阵 §⑥/§⑩/§⑬ 已读；§⑩ 与既有设计一致；§⑥ 偏离列入 V4 | 符合 | V4 需显式声明 | 阶段 2/3 记录偏离理由 | 待阶段 2 复验 | PASS |
| S1 | 输出落盘 | 阶段 1 验收 | 本文件位于 `docs/research/` | 符合 | 无 | 无 | — | PASS |
| S2 | 三类清单 | 阶段 1 验收 | 已核实 8 / 待核实 4 / 已排除 3 | 符合 | 无 | 无 | — | PASS |
| S3 | 攻击路径映射 | 阶段 1 验收 | §3 覆盖三技能全部 Ch4 路径 | 符合 | 无 | 无 | — | PASS |

**G0 结论：PASS**。进入阶段 2 `to-spec` ①；V4 须在规格中显式声明。

**上游复核修正（阶段 7）**：阶段 7 执行 `check_glossary.py` 时发现本文 V3 行两次使用 GLOSSARY `_Avoid_` 术语，已改为规范表述「演练目标」并复跑 `python scripts/check_glossary.py` → PASS。阶段 1 G0 在修正后保持 PASS。
