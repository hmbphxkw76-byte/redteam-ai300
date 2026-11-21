# Ch7 差距补强 — attack-mcp-tool 一手源调研

> **版本** v1.0 · **状态** 生效 · **调研日期** 2026-11-21（GMT+8）
> **目标技能** `skills/attack-mcp-tool/SKILL.md`（P0 · D7 · AI向量机）
> **性质** 阶段 1 交付物（增量补强 / 续推）：为 Ch7 四类技术缺口锁定一手事实，消除规格阶段猜测
> **行为唯一来源** `skills/attack-mcp-tool/SKILL.md`（本文件不改写 SKILL.md）
> **前置必读** `docs/research/osai-ai300-framework-decision.md`、`docs/research/osai-skill-framework-matrix.md`、`docs/research/attack-mcp-tool-canonical.md`（既有事实基线，本文件继承不重复）

## 1. 结论摘要（先读）

1. 本次补强的 4 类缺口均来自 OffSec AI-300 Ch7 一手源（课程文档：`D:\视频\OffSec   AI-300 Advanced AI Red Teaming\Ch7-Attacking-MCP-and-Tool-Surfaces.html`），逐项映射到 §7.1/§7.2/§7.3 章节与 Listing；它们**扩充攻击技术覆盖面**，不改变既有 `mcp-01..08` 步骤契约、双形态 seam 与证据片段结构。
2. 缺口 D1（目标侧真实差分）、D2（MCP Apps UI 渲染凭据窃取）、D3（路径穿越/symlink 沙箱逃逸）、D4（工具链 SSTI→RCE）在 Ch7 有明确原文与实验步骤；D5（shadow server 变体）标注为**合理推断**，不作为文档明确要求。
3. 框架组合沿用矩阵条目 `attack-mcp-tool`（D7/P0）：`promptfoo(MCP) + mcp-scan/agentic-radar + PyRIT HTTPTarget`（矩阵 §②，`docs/research/osai-skill-framework-matrix.md`）。PyRIT 仅深度补位，非主角（B9 合规）。
4. 新增能力用新步骤标识（`mcp-09`/`mcp-10`/`mcp-11`），不改写既有 8 步；这与 `report-exam` Attack Walkthrough 与 S2 证据契约夹具兼容（既有契约见 `tools/attack_mcp_tool/steps.py#STEP_SPECS`）。

## 2. 一手源事实（官方 URL / 课程章节逐条）

> 继承既有已核实事实见 `docs/research/attack-mcp-tool-canonical.md` §2（S-1..S-7）：OWASP MCP Top 10 2025 十项、MCP spec 2025-06-18 `tools/list`/`tools/call`/工具注解信任边界、`pyrit==1.1.0`。本文件只列**本次新增**缺口的一手源，不重复。

### 2.1 Ch7 攻击技术一手源（课程文档，逐条附章节/Listing）

| # | 事实（缺口对应） | Ch7 位置 | 关键原文要点 |
|---|---|---|---|
| C-A | D4 枚举前置：三类共享环境枚举技术（schema extraction / cross-tool correlation / permission mapping） | §7.1「Enumerating a Shared MCP Environment」，正文含 `db_query`、`github_search`+`fs_list`+`slack_history`、`pg_catalog` 示例 | 通过 LLM 代理调用工具即可完整枚举共享 MCP 环境，无需直连后端 |
| C-B | D1 投毒前后对照的判定信号 | §7.2「Tool Poisoning」，Listing（工具描述由 55 → 382 字符的 openapi.json 对照） | 描述长度异常膨胀是可观测的检测/对照信号 |
| C-C | D2 MCP Apps UI 渲染凭据窃取 | §7.2「MCP Apps / UI Rendering」，含 `srcdoc` 沙箱 iframe、JSON-RPC over `postMessage`、`_meta.ui.resourceUri`、AppBridge `tools/call` | 用户看到的是无 URL 栏/无发件人的伪造登录界面；harvester 经 AppBridge 调用 `manage_snippets` 保存 base64 凭据 |
| C-D | D2 shadowing（共享 server 代码改写影响所有用户） | §7.2「Shadowing」，SSH 改 `tools02` 服务器代码；不新增工具（schema 不变） | 只改服务端返回，工具清单与基线一致，规避审批 |
| C-E | D3 路径穿越 | §7.3「Path Validation Flaws」，`/data/documents/../.secrets/`；根因为前缀检查早于规范化 | 关联 **CVE-2025-53109 / CVE-2025-53110**（Anthropic 官方 MCP filesystem server） |
| C-F | D3 symlink 逃逸 | §7.3「Symlink Escape」，`vendor-docs` 软链指向 `prod.env`；`normpath`（逻辑）vs `realpath`（物理） | 正确修复：`os.path.realpath()` 而非 `os.path.normpath()` |
| C-G | D4 工具链 SSTI→RCE | §7.3「Tool Chaining」，`update_ticket`→`compile_sprint`→`render_report`；`lipsum.__globals__`、chr 编码分片、`{{7*7}}`→49 被 LLM 自算问题 | 注入点在早期工具、执行在后期工具；12 ticket + 1 触发 prompt 得 root reverse shell |
| C-H | D4 命令注入 | §7.3「Log Analysis」练习，`export_logs` 将聚合数据送入 shell（shell 元字符） | 下游工具管道是命令注入面 |

### 2.2 官方权威源（URL + 关键原文，2026-11-21 核实）

| # | 事实（缺口） | 官方一手源 URL | 关键原文 / 版本 |
|---|---|---|---|
| U-1 | MCP Apps UI 渲染机制（D2） | SEP-1865（Final）：<https://modelcontextprotocol.io/seps/1865-mcp-apps-interactive-user-interfaces-for-mcp>；Overview <https://modelcontextprotocol.io/extensions/apps/overview>；规范 <https://github.com/modelcontextprotocol/ext-apps/blob/main/specification/2026-01-26/apps.mdx>；AppBridge API <https://apps.extensions.modelcontextprotocol.io/api/classes/app-bridge.AppBridge.html> | "MCP Apps uses JSON-RPC 2.0 over `postMessage` for iframe-host communication"；"Tools: `tools/call` - Execute a tool on the MCP server"；"Tools are associated with UI resources through the `_meta.ui` field... `resourceUri?: string`"（扁平 `_meta["ui/resourceUri"]` 已弃用）；AppBridge "acts as a proxy between the host application and a view running in an iframe... forwards MCP server capabilities (tools, resources, prompts) to the view"。spec 版本 2026-01-26，SEP-1865 状态 Final |
| U-2 | OWASP MCP03 Tool Poisoning（D1/D2） | <https://owasp.org/www-project-mcp-top-10/2025/MCP03-2025%E2%80%93Tool-Poisoning> | "Tool poisoning occurs when an adversary compromises the tools, plugins, or their outputs that an AI model depends on - injecting malicious, misleading, or biased context to manipulate model behavior." 子技术含 rug pull / schema poisoning / **tool shadowing**（"introducing fake or duplicate tools to intercept or alter interactions"）。MCP Top 10 2025，Phase 3 Beta |
| U-3 | OWASP MCP09 Shadow MCP Servers（D5，辨析） | <https://owasp.org/www-project-mcp-top-10/2025/MCP09-2025%E2%80%93Shadow-MCP-Servers> | "'Shadow MCP Servers' refer to unapproved or unsupervised deployments of Model Context Protocol instances... frequently using default credentials, permissive configurations, or unsecured APIs." **辨析**：MCP09 指未授权的影子服务器**部署**；Ch7 的"shadowing"（改共享 server 代码影响所有用户）在 OWASP 中属 **MCP03 的 tool shadowing 子技术**，二者同类不同粒度，D5 归类需按此区分 |
| U-4 | CVE-2025-53109 symlink 逃逸（D3） | NVD <https://nvd.nist.gov/vuln/detail/cve-2025-53109>；GHSA-q66q-fx2p-7w4m（标题 "Path validation bypass via symlink handling"） | "Versions of Filesystem prior to 0.6.4 or 2025.7.01 could allow access to unintended files **via symlinks within allowed directories**." CWE-59；CVSS 4.0 **8.4 High**（CNA GitHub）；发布 2025-07-02；报告人 Elad Beber (Cymulate)；修复 commit `d00c60d` |
| U-5 | CVE-2025-53110 前缀碰撞绕过（D3） | NVD <https://nvd.nist.gov/vuln/detail/cve-2025-53110>；GHSA-hc55-p739-j48w（"Path validation bypass via colliding path prefix"） | "could allow access to unintended files **in cases where the prefix matches an allowed directory**." CWE-22；CVSS 4.0 **7.3 High**（CNA GitHub；NIST NVD 评分 N/A）。**版本不一致**：GHSA 元数据 Patched 写 0.6.3，NVD 与描述文本写 0.6.4 / 2025.7.01——规格中按 "0.6.4 / 2025.7.01（GHSA 元数据另列 0.6.3）" 记录 |
| U-6 | 路径校验正确做法（D3 修复对照） | 源码 <https://github.com/modelcontextprotocol/servers/blob/main/src/filesystem/path-validation.ts>；修复 commit `d00c60d` / `cc99bdab` | 两阶段校验：`path.resolve(path.normalize(...))` + `startsWith(normalizedDir + path.sep)`（防前缀碰撞）；再 `fs.realpath` 解析符号链接后重复校验（防逃逸）；不存在路径校验 realpath 后的父目录。对应 Python 语义：`normpath`+分隔符边界 + `realpath` 二次校验 |
| U-7 | 间接提示注入 → SSTI 权威依据（D4） | OWASP LLM01:2025 <https://genai.owasp.org/llmrisk/llm01-prompt-injection/>；OWASP WSTG-INPV-18 <https://owasp.org/www-project-web-security-testing-guide/v41/4-Web_Application_Security_Testing/07-Input_Validation_Testing/18-Testing_for_Server_Side_Template_Injection>；PortSwigger <https://portswigger.net/web-security/server-side-template-injection/exploiting> | LLM01: "Indirect prompt injections occur when an LLM accepts input from external sources, such as websites or files."；WSTG: "SSTI vulnerabilities occur when user input is embedded in a template in an unsafe manner and results in remote code execution on the server"，示例 `{{7*7}}`→`Hello 49!` |
| U-8 | Jinja2 `lipsum.__globals__` gadget（D4 载荷） | Ch7 §7.3 Figure 27/28（课程原文为一手源）；Jinja2 官方 <https://jinja.palletsprojects.com/en/3.1.x/> 仅作引擎能力佐证 | Ch7 原文："The `lipsum` built-in avoids this: it is a Jinja2 [function]"；载荷 `{{ lipsum.__globals__.keys() }}`、`{{ lipsum.__globals__['os'].popen('id').read() }}`。**标注**：未找到 `lipsum.__globals__` 的官方逐字利用说明，按**社区公开 gadget** 处理，不写成官方文档原话；SSTI→RCE 权威依据取 U-7 |

> 核实口径（2026-11-21 二次核实回填）：U-1..U-8 官方 URL 均实测可访问并逐条摘录。**三处关键修正**：① Ch7 原文用 `srcdoc` 描述 iframe，但官方 spec 实为"双层 iframe 沙箱代理 + 不同 origin + CSP"（见 §4 已排除）；② 修复 U-5 的 CVSS（二手 3.1/7.5 → 官方 CNA 4.0/7.3）并记录 GHSA/NVD 版本号不一致；③ 修复 U-3 的 shadowing 归属，并将 U-8 `lipsum` gadget 降格为社区技术、权威依据改用 U-7。

## 3. 缺口 → 攻击路径 / 对象映射（SKILL.md 对齐）

| 缺口 | 标识建议 | 演练目标可实测载体 | 实现层对象（沿用既有 seam） | 分类 |
|---|---|---|---|---|
| D1 目标侧真实差分 | mcp-04 增强（不新增标识） | agent-sse 同一 lab 前后两次 `tools/list` 快照 | `AgentSseClient.probe` / `poison.diff_surfaces` | ASI04 |
| D2 MCP Apps UI 投毒 | mcp-10（新） | 目标侧不可实测则本地 mock（`_meta.ui.resourceUri` 伪造界面） | `PoisonedMcpServer` 扩展 / `ToolDescriptor` | ASI04→ASI02 |
| D3 沙箱逃逸 | mcp-09（新） | 本地 mock 路径校验缺陷；目标侧 `MCP_12` untrusted 字段 | `JsonRpcMcpClient.call_tool` / 新 path probe | ASI03→ASI05 |
| D4 工具链 SSTI | mcp-11（新） | 目标侧 `MCP_14 chain_tool` / `MCP_06` 上下文载荷面 | `AgentSseClient.probe` / `SubStringScorer` | ASI02→ASI05 |
| D5 shadow server（推断） | 并入 mcp-10 | `MCP_09 shadow_mcp`（trust=shadow） | `ToolDescriptor.trust` | ASI04 |

## 4. 已排除（勿再当成事实）

| 名称/假设 | 排除依据 |
|---|---|
| 新增能力改写 mcp-01..08 契约 | 既有步骤标识是 S2 夹具机器判据（steps.py 头注）；改写会破坏 `report-exam` 证据复用与 CI 校验 |
| 演练目标存在裸 MCP 端点 / `ai_vector.txt` | 继承 `attack-mcp-tool-canonical.md` §5（T-1/T-6 全部 SPA 回退） |
| D5 是 Ch7 明确要求 | 课程原文描述 shadowing 场景但未列为独立实验目标，按合理推断处理，单列标注 |
| MCP Apps 用 `srcdoc` 沙箱（Ch7 措辞） | 官方 SEP-1865 / spec 2026-01-26 实为"host 经中间 Sandbox proxy 包裹 View，二者不同 origin，Sandbox 加载原始 HTML 并施加 CSP"；`srcdoc` 为课程简化表述，规格应按官方双层 iframe 沙箱代理建模（U-1） |
| `lipsum.__globals__` 有官方文档逐字说明 | 未找到官方逐字利用页；按社区公开 gadget 处理，权威依据取 OWASP WSTG-INPV-18 + PortSwigger（U-7/U-8） |
| 引入 MCP 官方 Python SDK / 三方依赖 | 违反 AC-17 与 ADR-0003 零外部依赖；沿用 `design.md` §6 否决结论 |

## 5. 待核实（带取证方式，不阻塞规格）

| # | 待核实项 | 取证方式 | 状态 |
|---|---|---|---|
| V-1 | MCP Apps `_meta.ui.resourceUri` / 沙箱 iframe / `postMessage` AppBridge 的官方 spec URL 与原文 | modelcontextprotocol.io/extensions/apps/overview + ext-apps spec 2026-01-26 | 已关闭 → U-1 |
| V-2 | OWASP MCP03 Tool Poisoning / MCP09 Shadow MCP Servers 官方标题与定义 | owasp.org/www-project-mcp-top-10 | 已关闭 → U-2/U-3 |
| V-3 | CVE-2025-53109 / CVE-2025-53110 编号、影响版本、根因、修复版本 | nvd.nist.gov + GHSA-q66q-fx2p-7w4m | 已关闭 → U-4/U-5 |
| V-4 | Jinja2 SSTI 经 `lipsum.__globals__` 的官方/权威说明 | jinja.palletsprojects.com + Ch7 §7.3 原文 | 已关闭 → U-6 |

## 6. 实现前必须取证的核实闸

1. **闸 A（差分真实性）**：D1 必须证明对照来自目标侧两次真实枚举；仅我方 server 基线的对照不得判完全生效（沿用 grade.py `capped_partial` 语义）。
2. **闸 B（本地 mock 诚实性）**：D2/D3/D4 若目标侧无对应 lab 可实测，须以本地 mock 自证并显式标注"目标侧未验证"，最高判部分生效，不夸大。
3. **闸 C（CVE 可复现性）**：D3 路径校验缺陷须在补丁前版本可复现；若演练目标已打补丁，记录为负结果并保留本地对照组。

## 7. 门禁记录（阶段 1 / G0）

**验收标准五项（§3.1）**：① 每条结论附一手源 → §2.1 Ch7 章节锚点 + §2.2 U-1..U-6 官方 URL；② 版本号明确 → `pyrit==1.1.0`（继承既有 canonical）、MCP spec 2026-01-26 / MCP Top 10 2025 / CVE 编号；③ 每条攻击路径有对象映射 → §3 表；④ 待核实项关闭 → §5 V-1..V-4 全关闭；⑤ 落盘 `docs/research/` → 本文件。

| 编号 | 检查项 | 依据 | 实测结果（命令 + 输出摘要） | 判定 | 不符合项 | 修正要求 | 复验 | 结论 |
|---|---|---|---|---|---|---|---|---|
| B7 | PyRIT 版本与对象图 | canonical §2 S-7 | `grep -n "pyrit==1.1.0"` 命中；无旧版编排器名 | 符合 | 无 | — | — | — |
| B8 | 可追溯性 | §2.1/§2.2 | 8 条 Ch7 锚点 + 6 条官方 URL 逐条附源 | 符合 | 无 | — | — | — |
| B9 | 框架选型合规 | 矩阵 §② | 组合 `promptfoo(MCP)+mcp-scan+PyRIT HTTPTarget` 取自矩阵，PyRIT 仅补位 | 符合 | 无 | — | — | — |
| B2 | 术语一致（§2.3） | check_glossary | `python scripts/check_glossary.py` → PASS（57 废弃术语） | 符合 | 无 | — | — | — |
| B1 | 结构（§2.3） | validate_skill | `python scripts/validate_skill.py` → PASS（16 技能） | 符合 | 无 | — | — | — |

**结论：PASS**。不符合项 0。阶段产物 8.4KB < research 无硬限；增量门禁符合 T2/T3（仅列本阶段变更项，三列压缩记录上游复核）。

## 8. 关联文档

- 行为唯一来源：`skills/attack-mcp-tool/SKILL.md`
- 既有事实基线：`docs/research/attack-mcp-tool-canonical.md`
- 术语基准：`GLOSSARY.md`
- 主线规范：`docs/operations/skill-mainline-workflow.md`
