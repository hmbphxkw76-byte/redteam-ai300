## Summary

按 OffSec AI-300 Ch7「Attacking MCP and Tool Surfaces」差距审阅，对 `attack-mcp-tool`（P0/D7）做增量补强。新增 3 步（mcp-09 沙箱逃逸 / mcp-10 MCP Apps UI 投毒+shadow / mcp-11 工具链 SSTI），不改写 mcp-01..08。

```text
ch7-gap
├── research   → ch7-gap.md (U-1..U-8 一手源)
├── spec       → issue #293 v1/v2 (11 AC)
├── design     → 三缝 + 1 UI 缝；escape/chain/uihost 模块
└── impl       → mcp-09/10/11 + grade 3 分支 + 19 例测试
```

## Evidence

| 项 | 改前 | 改后 |
|---|---|---|
| 步骤数 | 8（mcp-01..08） | 11（+mcp-09/10/11） |
| SRCDOC/AppBridge | 无 | uihost.py（官方双层 iframe 沙箱代理） |
| 沙箱逃逸 | 无 | escape.py（CVE-2025-53109/53110 判据 + realpath 修复对照） |
| 工具链 SSTI | 无 | chain.py（store→aggregate→render + {{7*7}} 探针） |
| shadow server | 无 | poison.shadow_surface（schema 全等判据） |

- 测试：62 → 81 例全绿；覆盖率 82.7% → 81.4%（≥80%）
- 端到端：mcp-09/10/11 均「部分生效」且 reason 诚实（目标侧信号未命中，本地 mock 不夸大）
- 证据命令可 copy/paste：`python -m tools.attack_mcp_tool.{escape,chain,uihost}` 实测可跑

## Merge Danger

- 单向门：mcp-01..08 契约与 S2 夹具标识不可回退；flag 双通道语义不变
- 双向门：GLOSSARY.md 与 scripts/tools_manifest.json 为共享文件——已 rebase 到 origin/main 8db9bc3 并逐项确认并集（我的 5 个 MCP 术语 + 远端 3 个 embedding 术语共存）；检出锁仍报 `_recon-ai-ch6_wt` 并发改 GLOSSARY，须串行处理
- 影响半径：attack-mcp-tool 包 + GLOSSARY + manifest（待注册新模块）；不影响其他 skill 运行时

---

| 纳管字段 | 值 |
|---|---|
| 能力域 | D7（MCP 与工具面） |
| 优先级 | P0 |
| 计分单元 | AI向量机（15 分） |
| 端到端演示 | `python tools/attack_mcp_tool/cli.py --target <AIVP> --path D E F` |
