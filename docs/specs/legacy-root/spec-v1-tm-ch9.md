## Problem Statement
既有 threat-model 的信任边界图只覆盖内网/域/立足点可达性，未覆盖 Ch9 的 IAM assume-role 链与 K8s 双身份能力互补链，编排层无法据此排序身份类攻击路径。

## Solution
新增纯分析模块，把两类身份链归一为有向图（节点=身份、边=可扮演/可读凭据/可建负载），输出最短路径与缺口；不改既有优先级攻击图语义。

## User Stories
1. 作为规划者，我想从角色链生成信任图，以便识别末端跨边界。
2. 我想从双身份能力生成可达路径，以便确认接管条件。
3. 我想不互补时记录缺口，以便不虚构可达。
4. 作为编排者，我想输出可被既有攻击图消费，以便零迁移。
5. 作为评审者，我想每结论可追溯 Ch9 锚点，以便审计。

## Implementation Decisions
- 纯函数图构建，零网络零框架（矩阵 ⑬）。
- 不执行 assume-role/token 提取（属攻击技能），只建模。
- 不改既有威胁模型文档结构与攻击图判据。

## Testing Decisions
- 只测外部行为：输入链/能力 → 图节点边、路径可达、缺口。
- 覆盖完整链/断链/互补/缺口四路径。

## Out of Scope
- 不生成实际凭据；不改 decoy/优先级图语义；不引入 MITRE 工具实现（仅方法论引用）。

## Further Notes
事实见 `docs/research/threat-model-ch9-canonical.md`（M-1..M-4）。
