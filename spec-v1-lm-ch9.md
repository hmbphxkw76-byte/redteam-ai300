## Problem Statement
Ch9 云/K8s 凭据狩猎产出大量凭据指纹，演练者缺少把它们即时登记入战利品登记簿的助手，易散落对话上下文或误落明文。

## Solution
新增指纹登记助手：接受前缀/长度/位置 + 来源主机 + 证据片段路径，追加 `凭据` 行，content 仅含脱敏指纹；复用既有登记簿解析/追加/校验。

## User Stories
1. 作为演练者，我想把每条凭据指纹即时登记，以便不散落。
2. 我想 content 只含脱敏表示，以便不落明文。
3. 我想来源主机与证据路径可追溯，以便报告复用。
4. 我想复用现有登记簿 schema，以便不引入第二事实源。
5. 我想缺位置时降级，以便不虚构。
6. 作为评审者，我想登记后校验通过，以便质量门。

## Implementation Decisions
- 新增独立函数，复用 `registry.append_row` / `LootRow`。
- 输入为指纹三元组 + 来源；不接收明文凭据。
- 不新增列、不改 TYPES/状态集合。
- 不引入任何攻击框架。

## Testing Decisions
- 只测外部行为：输入指纹 → 登记簿文本含预期行、content 无明文、validate PASS。
- 覆盖成功/缺位置/非法状态三路径。

## Out of Scope
- 不接收或存储明文凭据；不改 flag 双通道 / verify-evidence 逻辑。
- 不改动既有 loot-01..04 判据。

## Further Notes
事实见 `docs/research/loot-manage-ch9-canonical.md`（L-1..L-4）。
