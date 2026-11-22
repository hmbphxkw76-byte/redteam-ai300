---
name: threat-model
priority: P1
domain: D10
scoring_unit: 通用
trigger: recon-ai 资产清单已就绪，且进入考前 24h 规划窗口（§5.4），需把资产清单转化为优先级攻击图
input: recon-ai 资产清单（主机、服务、AI 面）、计分模型（§2.2 / §2.3，AI 向量机为最高杠杆）、既有诱饵机判定线索
output: 威胁模型文档（高价值资产 / 信任边界 / 最短攻击路径 / 诱饵判定与放弃理由；A2A 目标另含协调模式与攻击向量补标），可直接驱动编排顺序（§4.5）
---

# threat-model — AI 目标威胁建模

考前 24h 节奏（§5.4）下，把 `recon-ai` 的资产清单转化为**优先级攻击图**，先打最高杠杆目标、避开 0 分诱饵机（§5.3）。本技能覆盖 D10（AI 目标威胁建模），其输出（优先级攻击图）是 §4.5 编排流水线的入口驱动。与 `decoy-detect` 衔接（诱饵判定结论直接喂其复核），并拉动 `attack-rag` / `attack-embeddings` / `attack-infra` 等链式子技能。

## Ch9 身份链信任建模（加固版，不改既有图语义）

事实源 `docs/research/threat-model-c3-hardening-canonical.md`（M5-1..M5-7）。类型化结论 `tools/threat_model/ch9_c3_model.py#IdentityChainVerdict`；IAM 图 `tools/threat_model/ch9_identity_chain.py#iam_chain_graph`（L5-14/图3）、K8s 链 `#k8s_identity_chain`（L47-52/Table 2）；资产/边界/路径投影 `tools/threat_model/ch9_identity_chain.py#to_assets`、`#to_boundaries`、`#asset_ids_for`、`#shortest_for_chain`；下游引用探针 `tools/threat_model/ch9_c3_downstream.py#claim_ids`。

**约束**：资产 ID 稳定（`iam-<role>`/`k8s-sa-<name>`），attack-infra/foothold-traditional 按 ID 引用；信任边界与最短路径复用既有 `boundaries.shortest_paths`，不改诱饵判定与优先级图语义；纯分析、零网络、不执行 assume-role/token 提取。复验：`python scripts/verify_tm_c3_skill_refs.py && python scripts/verify_tm_c3_coverage.py --min 90`。

## 执行体

按「资产计分排序 → 信任边界与最短路径 → 诱饵机时间盒 → 优先级攻击图」四节推进；每节产出可机读/可复制的结论，缺失关键结论即判定未过质量门。

### 1. 资产计分排序（杠杆优先）

1. 依据 §2.2 / §2.3 计分模型对资产打分：**AI 向量机（15 分）> 独立机（15 分）> 传统向量机（10 分）> 链式入口（低杠杆）**。
2. 标注每个资产的攻击面归属：AI 应用层（D3/D4）、向量库/RAG（D5/D6）、基础设施（D9）、供应链（D8）、传统面（D1）。
3. 产出排序后的「高价值资产清单」，作为后续路径规划的输入。

### 2. 信任边界与最短攻击路径

1. 绘制信任边界：哪些资产在同一内网/域、哪些需先取得立足点（`foothold-traditional`）才可抵达、哪些 AI 向量机/独立机直接可达。
2. 对 top-N 高价值资产计算**最短攻击路径**（入口 → 横向 → 提权 → AI 利用 → flag），显式标注每一步对应的子技能（如 `attack-infra` 对应 D9、`attack-embeddings` 对应 D6）。
3. 产出「最短攻击路径图」（文本/表格），每条路径含：起止资产、必经阶段、预计耗时、依赖前置技能。
4. 多智能体/A2A 目标补标协调模式与三层信任边界（智能体间未验证输出/工具/系统）（文档依据 C1–C4 / Ch4 §4.1）：编排器（中心故障点；攻破即控制全局）、点对点（信任传播，可注入恶意对等体）、层级（垂直提权与上级冒充）、流水线（载荷跨阶段持久化与能力跳跃）；并标注框架特有风险（LangGraph 状态/检查点、AutoGen 代码执行与群聊、CrewAI 角色提示与记忆、Swarm handoff、A2A 发现机制冒充与解析面）。攻击面向量按输入/处理/输出/持久化四类登记，不在此重复攻击步骤。

### 3. 诱饵机时间盒识别（≤30min，§5.3）

1. 以**行为 / 漏洞缺失 / 无价值特征**三维度初筛疑似诱饵机：无 AI 基础设施面、无高价值服务、枚举反馈异常「过干净」或「信息缺失」。
2. **时间盒硬约束**：单台判定 ≤30min；超过即记录「判定不确定」并主动放弃，写入放弃理由，不在 0 分主机空耗（§5.3）。
3. 产出「诱饵判定清单」：每台含依据 + 放弃理由 + 时间戳，供 `decoy-detect` 复核。

### 4. 优先级攻击图（驱动编排）

1. 汇总上述三节，产出**优先级攻击图**：以最高杠杆资产为根、最短路径为边、诱饵机排除在外的有向图。
2. 输出明确编排顺序（§4.5）：先 AI 向量机/独立机，再传统链，最后域控 `proof.txt` 单次提交。
3. 结论以结构化片段落盘（markdown），可被 `report-exam` 的 Attack Walkthrough 与 `verify-evidence` 的校验清单直接复用。

### 5. Ch10 活体威胁建模增量（可选输入，不改上述四节）

当分析师提供假设、检测规则、信任边界或 RoE 约束时，在上述四节基础上增量建模（依据 OffSec AI-300 Ch10；事实源 `docs/research/threat-model-ch10-canonical.md`）：

1. **假设登记册**：逐条记录 Observation/Hypothesis/Confidence/Source/Status；置信度=来源可靠性而非正确概率，LOW/缺证（"absence of evidence"）标为验证任务、不驱动攻击规划；证伪生成派生假设并重算路径。
2. **信任边界实体化**：按"从→到/信任类型/强制机制/验证状态/进攻含义"五要素登记，区分策略强制与推理强制边界；信任区按 VALIDATED/UNVALIDATED/INFERRED 三态标注；无强制机制标 TRUST_GAP，身份在工具边界塌缩标归属丢失。
3. **升级路径与 Go/No-Go**：路径标注跨越边界、依赖假设门（GO/HOLD/BLOCKED）、检测风险；输出"信息可用/缺失/验证成本/决定"决策矩阵；计划是决策树，随情报剪枝。
4. **RoE 硬过滤（双轨）**：被禁止路径移出执行计划、转为报告风险发现；不得"若客户批准"式条件保留。
5. **皇冠珠宝 + ATLAS + 简报**：按当前知识进攻价值排序（与考试计分并存）；组件映射 MITRE ATLAS 七技术 ID（前置未验证标 applicable if）；产出六段版本化攻击情报简报，版本史即决策日志。

> 本节为增量：既有四节标识、质量门四项语义、诱饵时间盒、考试计分与 §4.5 编排均保持不变；无相关输入时不产出增量节。

## 质量门

以下结论**必须**全部产出，缺失任一即判定未过门禁，不得进入下一步：

- **高价值资产清单**（按 §2.2/§2.3 计分排序，明确 AI 向量机/独立机排名）。
- **信任边界 + 最短攻击路径图**（每条路径标注起止、阶段、耗时、依赖子技能；A2A 目标另含协调模式、三层信任边界与四类攻击向量）。
- **诱饵判定清单**（依据 + 放弃理由 + 时间戳，时间盒 ≤30min）。
- **优先级攻击图**（驱动 §4.5 编排顺序，诱饵机已排除）。
- 上述产物统一以 markdown 结构化片段落盘，与 `report-exam` / `verify-evidence` / `decoy-detect` 可衔接（复用 `loot-manage` 索引习惯）。

## 校验标准

- 威胁模型可被技术读者 **copy/paste 逐步复现**（§6.1），资产排序与路径推导有据可查。
- 产出与 `decoy-detect` 的诱饵复核、`report-exam` 的 Attack Walkthrough 直接兼容，可无损复用。
- A2A 协调模式与信任边界补标可被 `attack-multi-agent` 按资产 ID 直接引用，不在攻击技能内重复建模。
- 术语符合 `GLOSSARY.md`（用「诱饵机」「AI向量机」「独立机」「威胁模型」等规范词，禁用 `_Avoid_` 废弃术语）。

## 失败与豁免

- 若目标无可用高价值 AI 面，记录判定依据后改走传统向量机链（`foothold-traditional`），不阻塞整体规划。
- 若资产清单未给出 A2A Agent Card 或编排端点线索，协调模式记 `UNDETERMINED`，不虚构拓扑或信任关系。
- 若诱饵机判定不确定（信息不足），严格按 §5.3 时间盒 ≤30min 结束并主动放弃，记录理由，不在 0 分主机空耗。
- 若最短路径依赖的前置技能（如 `attack-infra`）尚未就绪，显式标注该路径为「待补」，不虚构可达性。
- 本技能仅做规划产出，**不含任何实际攻击利用**，所有结论须由对应攻击子技能在实战中验证。
