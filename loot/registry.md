# 战利品登记簿 (loot registry)

> 单一事实源（GOVERNANCE §5.2）。每行一条战利品；「证据片段路径」指向 `collect_evidence.py` 产物，不重复存证据本体。

| 编号 | 类型 | 内容 | 来源主机 | 证据片段路径 | 时间戳 | 状态 | 双通道 |
|---|---|---|---|---|---|---|---|
| L-1 | flag | sk-i3A72OADzyPexVJANUxmJNl1ooUONVXS | 192.168.40.189 | evidence/attack-mcp-tool-verify/mcp-08.md | 2026-11-15T17:53:31+08:00 | 已取证 | 面板=sk-i3A72OADzyPexVJANUxmJNl1ooUONVXS；截图=evidence/attack-mcp-tool-verify/mcp-08.md |
| L-2 | 凭据 | service_token:sk-i3A72OADzyPexVJANUxmJNl1ooUONVXS | 192.168.40.189 | evidence/attack-mcp-tool-verify/mcp-08.md | 2026-11-15T17:53:31+08:00 | 有效 | — |

## 攻击路径

<!-- 每完成一段攻击路径追加一行：- 入口 A → B（trad-04 flag）→ C（trad-07 flag） -->
- 入口 http://192.168.40.189 (AIVP) → MCP_01 工具滥用（mcp-05/mcp-07 完全生效）→ 凭据泄露 flag（mcp-08 面板校验 success=True）
