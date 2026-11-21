# attack-mcp-tool Ch7 增量 — 术语映射表

> **性质** 阶段 7 交付物：消除规格、设计、代码、报告之间的语义漂移
> **术语基准** `GLOSSARY.md`（唯一定义处，本文件不重复定义）
> **一手源** `docs/research/attack-mcp-tool-ch7-gap.md`（U-1..U-8）

| SKILL/规格概念 | GLOSSARY 术语 | 调研事实锚点 | 代码标识符（阶段 8 落点） | 首现阶段 |
|---|---|---|---|---|
| MCP Apps UI 投毒 | MCP Apps (MCP 应用) | U-1（SEP-1865 / spec 2026-01-26） | `uihost.py` / `UiHostClient` / `make_ui_resource` | 8（mcp-10） |
| AppBridge 外泄通道 | AppBridge (应用桥) | U-1 | `UiHostClient.probe` / postMessage 取证字段 | 8（mcp-10） |
| 路径穿越 + symlink | 沙箱逃逸 (sandbox escape) | U-4/U-5/U-6（CVE + 源码） | `escape.py` / `prefix_bypass` / `symlink_escape` / `realpath_fix_check` | 8（mcp-09） |
| store→aggregate→render | 工具链注入 (tool-chain injection) | U-7/U-8（OWASP WSTG / PortSwigger） | `chain.py` / `build_chain` / `ssti_probe` / `cmd_inject` | 8（mcp-11） |
| 目标侧前后对照 | 目标侧差分 (target-side diff) | 调研 §6 闸 A | `runner.py` mcp-04 ctx `diff_source=target-sse` | 8（mcp-04 增强） |
| shadow server（推断） | 信任级别 (trust level) 的 shadow 值 | U-3（MCP03 子技术辨析） | `poison.py` / `shadow_surface()` | 8（mcp-10 变体） |
| 效果封顶 | 效果等级（既有） | 调研 §6 闸 B | `grade.py` / `capped_partial` | 8（grade 扩展） |

## 门禁记录（阶段 7 / G0）

| 编号 | 检查项 | 依据 | 实测结果 | 判定 |
|---|---|---|---|---|
| B1 | 结构 | `validate_skill` | PASS（16 技能） | 符合 |
| B2 | 术语一致 | `check_glossary` | PASS（57 废弃术语） | 符合 |
| 验收① | 映射覆盖新概念 | 本表 | 7 概念全覆盖规格与设计 | 符合 |
| 验收② | GLOSSARY 含定义与来源 | GLOSSARY 5 条新术语 | 每条含定义 + 一手源锚点 | 符合 |
| 验收③ | check_glossary 通过 | 命令输出 | PASS | 符合 |

**结论：PASS**。不符合项 0。新增术语 5 条均带来源；GLOSSARY 体量控制在精简范围（C7 精神）。
