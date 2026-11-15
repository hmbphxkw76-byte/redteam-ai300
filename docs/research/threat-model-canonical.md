# threat-model 规范事实库（canonical references）

> **性质**：研究/事实文档（非规范正文）。供 `skills/threat-model/SKILL.md` 落地为 `tools/threat_model/` 时使用。
> **核验日期**：2026-11-15（GMT+8）。每条结论附一手来源；待核实项逐条命名并给出取证方式。
> **依据**：GOVERNANCE.md §2.2/§2.3（计分模型）、§4.5（编排顺序）、§5.3（诱饵时间盒）、`skills/threat-model/SKILL.md`、`tools/recon_ai/model.py`（`ASSET_FIELDS` 七字段契约）、`docs/research/osai-skill-framework-matrix.md` 条目 ⑬。

---

## 1. 能力域与技能定位

- **能力域 D10**：AI 目标威胁建模（GOVERNANCE §3.1 编号 D10）＝高价值资产、信任边界、攻击路径。
- **优先级 P1**（GOVERNANCE §4.4）：显著提升 24h 效率，不必然决定及格，属执行前置。
- **评分单元**：通用（前置），本身不直接产出 flag；其产出驱动下游攻击编排顺序（§4.5）。
- **框架组合（矩阵 ⑬）**：**方法论（MITRE ATLAS / OWASP LLM Top10 / OWASP Agentic Top10）+ 文档/图表 + 许可 AI 助手**；无专用攻击框架，框架是被建模对象。PyRIT **不出现**（规划技能，不含攻击利用）。

## 2. 一手源核实（canonical frameworks）

| 方法论 | 官方 URL（已 WebFetch 核实） | 版本/状态 | 在本技能的角色 |
|---|---|---|---|
| MITRE ATLAS | `https://atlas.mitre.org/`（标题确认 "MITRE ATLAS™"） | 持续维护 | 战术/技术分类树，映射 AI 攻击路径到 ATLAS TTP |
| OWASP Top 10 for LLM Applications | `https://owasp.org/www-project-top-10-for-large-language-model-applications/`（已并入 OWASP GenAI Security Project，最新清单 `https://genai.owasp.org/llm-top-10/`） | 2025 版为 OSAI 考试口径 | LLM 应用风险分类，标注资产攻击面（D3/D4/D5/D6/D7） |
| OWASP Agentic AI（Securing Agentic Applications / Agentic App Security initiative） | `https://genai.owasp.org/`（"Agentic App Security" 倡议，文档 "Securing Agentic Applications V2"） | 2025–2026 持续更新 | 多智能体/A2A 威胁分类，标注 D4 |

**取证方式**：考试前以 `WebFetch`/`curl` 复核上述 URL 的最新版本号与条目编号；若版本漂移，仅在 `skills/threat-model/SKILL.md` 显式标注偏离理由（GOVERNANCE §8.3）。

## 3. 计分模型（一手源：S1/S3，GOVERNANCE §2.2/§2.3）

- **8 计分目标 = 100 分**：AI向量机 15 分/台，传统向量机 10 分/台，独立机 15 分，域控 5 分（仅可提交一次）。
- **推导（非官方原文）**：链式主机构成 = 4 台 AI向量机（60）+ 2 台传统向量机（20）；+ 独立机 15 + 域控 5 = 100（GOVERNANCE §2.2.2）。
- **及格线 75/100**（S1/S3）；工程目标分 ≥85（§2.3.4）。
- **最高杠杆组合（推导）**：4 AI向量机（60）+ 独立机（15）= 75，无需传统/域控即可及格 → **AI 向量是最高杠杆**（ADR-0002，§2.3.2）。
- **排序优先级（SKILL 执行体 §1）**：AI向量机(15) > 独立机(15) > 传统向量机(10) > 链式入口(低杠杆)。

> 待核实：链式"4 AI + 2 传统"为推导（S3 未明示），不影响威胁建模排序结论，但影响训练权重（已在 `osai-ai300-framework-decision.md` §6 标注）。

## 4. 输入契约：recon-ai 资产清单（七字段）

源：`tools/recon_ai/model.py` `ASSET_FIELDS`（唯一权威定义，不可转抄，引用路径 `#锚点`）。

| 字段 | 含义 | 来源 |
|---|---|---|
| `asset_id` | 稳定唯一标识，如 `ai-llm-<host>-01` | recon_ai/model.py `ASSET_FIELDS[0]` |
| `category` | 组件类别（7 类：LLM引擎/模型服务/RAG库/向量库/agent系统/MCP工具面/护栏） | 同上 `[1]` |
| `product` | 产品/引擎（vLLM、Milvus、LangChain…） | 同上 `[2]` |
| `version` | 版本或版本区间 | 同上 `[3]` |
| `endpoint` | 暴露端点/端口 | 同上 `[4]` |
| `credential_hint` | 仅线索指纹（`Bearer-<前8位哈希>`），不落盘明文 | 同上 `[5]` + SKILL OPSEC |
| `evidence_step` | 关联证据片段 step_id（如 `loot/recon-03-rag-lib.md`） | 同上 `[6]` |

**关键约束**：recon 资产清单**不含**计分分类（AI向量/独立/传统/域控/诱饵）与信任边界/可达性。这些分类是威胁建模的**分析师输入**，须由独立分类层补充（见设计阶段 seam：`classify`）。`tools/threat_model/` 以 recon 七字段为只读输入，叠加 `score_class`/`attack_surface`/`trust_zone`/`reachable` 三类分析师标注。

## 5. 诱饵机时间盒（§5.3，一手源 GOVERNANCE §2.1 + SKILL）

- **数量**：2 台故意不设漏洞（0 分）；共 10 台主机（6 链式 + 1 独立 + 1 域控 + 2 诱饵）（§2.1.1）。
- **三维度初筛**：① 行为（无 AI 基础设施面、无高价值服务）；② 漏洞缺失（枚举反馈异常"过干净"/"信息缺失"）；③ 无价值特征（无计分项）。
- **硬约束**：单台判定 ≤30min；超时即记"判定不确定"并主动放弃，写入放弃理由 + 时间戳，不在 0 分主机空耗（`decoy-detect` 复核）。
- **术语**：以「诱饵机」为唯一规范词（其禁用同义表述见 GLOSSARY.md 的 `_Avoid_` 段）。

## 6. 编排顺序（§4.5，GOVERNANCE）

固定流水线（任一未过质量门不得推进）：

```
威胁建模(threat-model) → 侦察枚举(recon-ai) → 立足点(foothold-traditional)
  → 链式横向 + AI向量利用(attack-ai-agent/rag/mcp-tool/embeddings)
  → 独立机(attack-mcp-tool 等) → 战利品沉淀(loot-manage)
  → 域控收敛(如取分) → 证据校验(verify-evidence) → 报告生成(report-exam)
```

threat-model 的**优先级攻击图**须显式输出此编排顺序：先 AI向量机/独立机 → 再传统链 → 最后域控 `proof.txt` 单次提交（§4.5 + SKILL 执行体 §4）。

## 7. 已核实 / 待核实 / 已排除

**已核实（一手源）**
- 计分模型 §2.2/§2.3，排序优先级，诱饵时间盒 §5.3，编排 §4.5。
- 三大方法论官方 URL（§2 WebFetch 核实）。
- recon 七字段契约（`tools/recon_ai/model.py` `ASSET_FIELDS`）。
- 框架组合 = 方法论+文档+许可 AI，无 PyRIT（矩阵 ⑬）。

**待核实（取证方式已给出）**
- OWASP LLM/Agentic Top10 最新版本号（考试前 WebFetch 复核）。
- 链式"4 AI + 2 传统"推导确认（S3 原文）。
- 实际考试环境资产分类（仅实战 24h 窗口可得，先于本技能输入）。

**已排除（不纳入实现）**
- 任何实际攻击利用（SKILL「失败与豁免」：仅规划产出）。
- PyRIT / garak / promptfoo 攻击框架（威胁建模阶段不调用；框架是被建模对象）。
- 凭据明文处理（沿用 recon `credential_hint` 指纹，不解密）。

## 8. 对象映射（攻击路径 → 框架/子技能）

| threat-model 输出路径 | 下游驱动子技能/框架 | 映射依据 |
|---|---|---|
| AI向量机最短路径 | `attack-ai-agent`(D3)/`attack-rag`(D5)/`attack-mcp-tool`(D7)/`attack-embeddings`(D6) | GOVERNANCE §4.5 + 矩阵 ①–③⑨ |
| 独立机路径 | `attack-mcp-tool` 等（D7/独立机） | 矩阵 ② |
| 传统链/域控 | `foothold-traditional` + Kali 工具链 | 矩阵 ⑦ + §4.5 |
| 诱饵放弃 | `decoy-detect` 复核 | SKILL 衔接 + 矩阵 ⑭ |
| 证据/报告衔接 | `verify-evidence`/`report-exam`/`loot-manage` | SKILL 校验标准 + §4.5 |

## 9. 验收锚点（供 to-spec 阶段引用的事实源）

- 术语基准：`GLOSSARY.md`（诱饵机、AI向量机、独立机、资产清单、信任边界待补）。
- 质量门：`skills/threat-model/SKILL.md` 第四节（高价值资产清单/信任边界+最短路径/诱饵判定/优先级攻击图）。
- 证据衔接：复用 `collect_evidence.py` 片段习惯与 `loot-manage` 索引；本技能**不直接调用** `collect_evidence`（规划技能，无逐步命令取证），仅产出可被下游按资产ID引用的结构化片段。

---

## 阶段门禁记录（阶段 1 · research · G0）

| 基线 | 判定 | 证据命令 |
|---|---|---|
| B7 PyRIT 版本与对象图 | 符合（不适用） | `grep` 检索旧版对象名（B7 所列三类）于本文件 → 无命中（规划技能，无 PyRIT 对象图） |
| B8 可追溯性 | 符合 | 文档含 3 条一手 URL（atlas.mitre.org / owasp.org / genai.owasp.org）+ S1/S3 引用 + 矩阵 ⑬ |
| B9 框架选型合规 | 符合 | 框架组合 = 方法论+文档+许可 AI（矩阵 ⑬）；无 PyRIT/garak/promptfoo 攻击框架调用 |

**复验命令**：`python scripts/check_glossary.py`（术语待阶段 7 补全）；`wc -c docs/research/threat-model-canonical.md`（8001 ≤ 16000）。
**结论**：PASS。不符合项 0。下游阶段 2/3/6/8 复用本事实源，不重复检索。
