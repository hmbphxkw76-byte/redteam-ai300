## Problem Statement
Ch9 的 Sidecar 运行时拦截与 MinIO 工件投毒在语义上相邻，若无显式边界，attack-infra B2 与 attack-supply-chain 会重复实现或互相越界。

## Solution
新增确定性边界判定函数：输入观察文本，输出 owner（本技能/attack-infra/无）+ reason + confidence；在 SKILL.md 声明能力边界与转交规则。不改既有投毒判据。

## User Stories
1. 作为编排者，我想判定一项观察归哪个技能，以便不重复实现。
2. 我想双向信号时标记歧义，以便人工复核。
3. 作为评审者，我想 SKILL.md 显式声明边界，以便审计。
4. 作为演练者，我想不改既有投毒流程，以便零回归。

## Implementation Decisions
- 纯字符串信号分类，零网络零框架；不接收凭据。
- 产物信号优先于运行时信号（投毒是本技能唯一职责）。
- 不改动既有 Ch8 模块。

## Testing Decisions
- 只测 classify 外部行为；覆盖 runtime/artifact/ambiguous/no-signal 四路径。

## Out of Scope
- 不实现运行时拦截（attack-infra B2）；不改 Ch8 G1-G14 判据；不引入新攻击载荷。

## Further Notes
事实见 `docs/research/attack-supply-chain-ch9-canonical.md`（S-1..S-4）。
