# threat-model Ch10 对齐实现 — 调研事实库（阶段 1 · research）

> **版本** v1.0 · **日期** 2026-11-22（GMT+8） · **技能** `skills/threat-model/SKILL.md`（D10/P1） · **性质** 阶段 1 交付物
> **一手源** `D:\视频\OffSec   AI-300 Advanced AI Red Teaming\Ch10-Threat-Modeling-for-AIEnabled-Targets.html`（45MB，内嵌媒体；stdlib HTMLParser 抽纯文本 1120 行，锚点 L 为抽取后行号）
> **继承事实源**（不重复转抄，走 C1 指针）：`docs/research/threat-model-canonical.md`（§2 官方 URL 已 WebFetch 核实、§4 七字段契约、§9 验收锚点）、`docs/research/threat-model-ch10-gap.md`（M1–M18 + A1–A8，本任务实施清单）、`docs/operations/threat-model-design.md`（8 模块 + seam 清单）、矩阵条目 ⑬（MITRE ATLAS/OWASP + 文档 + 许可 AI，无 PyRIT）。
> **固定阅读**（§1.4 已读）：`osai-ai300-framework-decision.md`（best-of-breed 分层栈）、`osai-skill-framework-matrix.md`（⑬ threat-model = 方法论 + 文档 + 许可 AI，框架是被建模对象，无专用攻击框架）。

## 1. 已核实（Ch10 一手源逐条，附锚点）

### 1.1 活体模型与迭代节奏（M1/M2）
| # | 事实 | Ch10 锚点 |
|---|---|---|
| R-01 | 威胁模型不是开工前构建后执行的产品，而是随每条情报、每个被验证/废弃的假设、每个消除理论路径的范围约束而演进的活体产物 | §10 引言 L10–17 |
| R-02 | 输出为攻击情报简报（attack intelligence brief），基于"当前所知"指明下一步攻击哪个目标 | §10 L23–25 |
| R-03 | 方法论归纳为 observe → hypothesize → test → update → decide → act | §10.3 L1103–1112 |

### 1.2 假设登记册（M4/M5/M15）
| # | 事实 | Ch10 锚点 |
|---|---|---|
| R-04 | 假设登记册六字段：ID / Observation / Hypothesis / Confidence / Source / Status | §10.1 Table 1（L133–187） |
| R-05 | 生命周期：观察 → 验证测试 → VALIDATED（驱动攻击规划）或 INVALIDATED（生成新假设），反馈环是迭代建模的核心 | §10.1 L128–132、Figure 1 |
| R-06 | 置信度反映**来源可靠性**，不是假设为真的概率 | §10.1 L188–190 |
| R-07 | A-07 为 LOW + "absence of evidence"：LOW 置信假设驱动早期验证任务，不驱动攻击规划；把信息缺失当成漏洞确认是最常见错误之一 | §10.1 L192–200 |
| R-08 | 登记册随每条新情报更新：晋升/降级假设、调整置信、新增条目 | §10.1 L201–206 |
| R-09 | 证伪的价值：发现路径关闭后尽早重定向，"learn that something is not possible can be more valuable than learning something might be plausible" | §10.1 L652–661 |
| R-10 | 被否定的路径产生新假设（A-16）并重生新路径；A-15 失效则约束路径（改用 `aws ssm send-command`）而非消除 | §10.2 L1021–1057 |

### 1.3 信任边界与信任区（M9/M10/M17/M18）
| # | 事实 | Ch10 锚点 |
|---|---|---|
| R-11 | 信任边界定义：组件接受另一组件输入/指令而不独立验证之处；AI 系统新增"由推理而非策略强制的边界"（LLM 分类判定无策略 backing），利用方式是输入操纵而非认证绕过 | §10.2 L704–713 |
| R-12 | 信任边界表字段：ID / From→To / Trust Type / Enforcement / Validation Status / Offensive Implication；共 TB-1..TB-8 | §10.2 Table 8（L714–779） |
| R-13 | Validation Status 三态：VALIDATED / UNVALIDATED / INFERRED；四个边界（TB-1/TB-5/TB-7/TB-8）仍未验证或推断，属正常，须标注区分已验证攻击面与理论攻击面 | §10.2 L770–779 |
| R-14 | TB-5（MCP→Vault）：AppRole 服务身份，身份在边界塌缩致 agent 级审计 trail 丢失（A-12c） | §10.2 Table 8 TB-5、L426–438 |
| R-15 | 信任区=共享特权级别区域；实线边界 VALIDATED，虚线 ((?)) 为 UNVALIDATED 强制机制 | §10.2 Figure 4 + L780–786 |
| R-16 | 最危险路径不突破信任边界，而是流经"信任从未强制的缺口"（未认证向量库、无法区分 agent 的 Vault、信任分类的编排器）——非 bug 而是牺牲安全的架构决策 | §10.3 L1113–1121 |

### 1.4 升级路径 / Go-No-Go / 简报（M11/M12/M13/M14）
| # | 事实 | Ch10 锚点 |
|---|---|---|
| R-17 | 三条升级路径：Path 1（Remediation token 窃取→直接 MCP 滥用，主路径）、Path 2（staging 向量投毒→间接影响 Remediation）、Path 3（情报提取，支持路径，EXECUTE FIRST） | §10.2 L797–868 |
| R-18 | 每条路径含 Go/No-Go 门（依赖未验证假设）、时间约束（24h MCP 报告时钟）、检测风险（LOW/MEDIUM）；计划是决策树不是脚本，须随情报剪枝 | §10.2 L804–823、L916–923 |
| R-19 | RoE 是硬约束：投毒仅 staging Qdrant(:16333)，禁生产库写/DoS；禁止路径从执行计划删除但仍作为风险发现进最终报告，不得写"if client approves" | §10.1 L85–93、L286–305 |
| R-20 | Go/No-Go 决策矩阵列：Decision Point / Information Available / Information Missing / Time Cost to Validate / Decision（GO/HOLD） | §10.2 Table 9（L875–910）、Figure 8 |
| R-21 | 攻击情报简报六段：TARGET SUMMARY / CROWN JEWELS / ASSUMPTION REGISTER STATUS / SCOPE CONSTRAINTS / ESCALATION PATHS / NEXT ACTIONS，含 Classification / Engagement Day / Brief Version | §10.2 Listing 8（L930–999） |
| R-22 | 简报版本史 = 决策日志（v1.0 Day1 假设 → v1.1 Day2 纳入侦察结果并否定扁平凭证模型 → v1.2 Day3 集成检测规则与 go/no-go 门）；价值在"诚实"非"完整" | §10.2 L1003–1020 |

### 1.5 皇冠珠宝 / ATLAS / 检测规则（M6/M7/M8/M16）
| # | 事实 | Ch10 锚点 |
|---|---|---|
| R-23 | 皇冠珠宝按"当前知识下的进攻价值"排序并重排，字段 Rank / Asset / Location / Offensive Value / Confidence，另标访问状态（OBTAINED / ACCESSIBLE / UNVALIDATED / BEHIND N BOUNDARIES） | §10.1 Table 5（L459–494）、L495–503、Listing 8 L940–946 |
| R-24 | MITRE ATLAS 映射表：Component / ATLAS Technique / Technique ID / Application Given Current Access；7 个 ID：AML.T0044 / T0025 / T0020 / T0048 / T0043 / T0010 / T0040 | §10.1 Table 6（L517–549） |
| R-25 | 多项 ATLAS 技术标"applicable if"：前置假设高置信确认前不进入执行计划；ATLAS 映射随登记册演进 | §10.1 L550–555 |
| R-26 | 检测规则提取（Listing 7，5 条规则）派生假设 A-12..A-15；A-15 置信 MEDIUM 因仅见 5 条规则，Qdrant 外可能有其他检测 | §10.1 L561–619 |

## 2. 待核实（带取证方式，不阻塞实现）
| 项 | 状态 | 取证方式 |
|---|---|---|
| ATLAS 技术**官方显示名**逐字 | 官方站 `atlas.mitre.org` 可达、标题 "MITRE ATLAS™"（canonical.md §2 于 2026-11-15 WebFetch 核实）；本次 WebFetch 仅返回 cookie 横幅（SPA），详情名不可定向提取；CDP 未连接（浏览器未开远程调试）。实现按 Ch10 Table 6 院校映射取名，不虚构官方逐字名 | 用户在浏览器开 `edge://inspect/#remote-debugging` 后走 CDP；或考前 WebFetch 复核 |
| OWASP LLM/Agentic Top10 最新版本号 | canonical.md §2 已标"待核实" | 阶段 8 前 WebFetch `genai.owasp.org/llm-top-10/` 复核；偏离须按 §8.3 声明 |
| ATLAS 版本/日期 | 官网持续维护，无静态版本号可见 | 同上 |

## 3. 已排除（不纳入实现）
- PyRIT / garak / promptfoo 攻击框架：矩阵 ⑬ 明确威胁建模为分析活动、框架是被建模对象；本任务纯规划产出，B7 不适用（无对象图），B9 合规。
- 任何实际攻击利用：`SKILL.md`「失败与豁免」仅规划产出；Ch10 内容为建模方法论，不是利用步骤。
- 改动 recon 七字段契约（`ASSET_FIELDS`）：A6 的观察链走 `classify` 分析师覆盖层承载，遵循 design.md §7「分析师分类层」否决自动推断的既有决策。
- 删除既有四节 / `quality_gate()` 四项 / 诱饵时间盒 / 考试计分 / §4.5 编排：项目特化，Ch10 无对应，非差距。

## 4. 实现侧现状锚点（代码事实，供阶段 6 设计消费）
- `tools/threat_model/` 8 模块：`model`（`SCORE_TABLE`/`RANK_INDEX`/`STAGE_TEMPLATE`/`SUBSKILL` + 4 dataclass）、`classify.enrich`（覆盖层 seam）、`score`、`boundaries`（`trust_boundaries` 按 `trust_zone` 分组；`shortest_paths` 套模板）、`decoy`（时钟 seam）、`graph`、`render`（四节）、`cli`（唯一 I/O）、`__init__.build_threat_model`（一次性构造）。
- `ThreatModel.quality_gate()` 四项；`tests/threat_model/` 32 例（test_threat_model.py 25 + evidence_contract 7）。
- 依赖单向：领域模块只 import `model`，`model` 不 import 本项目模块；cli 唯一 I/O（design.md §3）。
- 输出契约：四节 markdown + 质量门，证据片段兼容 `report-exam`/`verify-evidence`（canonical.md §9）；`report_exam.index.parse_fragment` 对 flag 段原值块敏感。

## 阶段门禁记录（阶段 1 · research · G0）

| 基线 | 判定 | 证据命令 / 摘要 |
|---|---|---|
| B7 PyRIT 版本与对象图 | 符合（不适用） | 规划技能无 PyRIT/对象图；矩阵 ⑬ 无专用框架；B7 所列三类旧版编排器对象名命中 0 处 |
| B8 可追溯性 | 符合 | 每条 R-01..R-26 附 Ch10 §/L/Table/Listing 锚点；ATLAS 官方 URL 经 canonical.md §2 核实；待核实项给出取证方式 |
| B9 框架选型合规 | 符合 | 组合 = MITRE ATLAS/OWASP 方法论 + 文档 + 许可 AI（矩阵 ⑬），无 PyRIT/garak/promptfoo |

**复验命令**：`wc -c docs/research/threat-model-ch10-canonical.md`（≤16000）；B7 三类旧版编排器对象名 `grep -c` 命中 0（本文件为规划事实库，无对象图）。
**结论**：PASS。不符合项 0。下游阶段 2/3/6/8 复用本事实源，不重复检索。
