# 战利品登记簿 (loot registry)

> 单一事实源（GOVERNANCE §5.2）。每行一条战利品；「证据片段路径」指向 `collect_evidence.py` 产物，不重复存证据本体。

> **数据分类（R01）**：当前登记内容为**演练靶场夹具**——DVAA / MCP lab 演示值（字面含 `dvaa-demo` / `do-not-use-in-production` / `test-key`），非真实生产凭据或考试 flag；来源主机为 RFC1918 私有实验网段（不可公网路由）。
> **真实考试政策**：考试窗口的真实 flag/凭据登记簿**不得入公开版本库**——按合规 §1 与 GOVERNANCE §6.1 落 gitignored `evidence/` + `loot/*`，本地供 `verify-evidence` 双通道机检，不提交。详见 `docs/operations/osai-submission-compliance.md` §2 决策 2 补注。

| 编号 | 类型 | 内容 | 来源主机 | 证据片段路径 | 时间戳 | 状态 | 双通道 |
|---|---|---|---|---|---|---|---|
| L-1 | flag | sk-i3A72OADzyPexVJANUxmJNl1ooUONVXS | 192.168.40.189 | evidence/attack-mcp-tool-verify/mcp-08.md | 2026-11-15T17:53:31+08:00 | 已取证 | 面板=sk-i3A72OADzyPexVJANUxmJNl1ooUONVXS；截图=evidence/attack-mcp-tool-verify/mcp-08.md |
| L-2 | 凭据 | service_token:sk-i3A72OADzyPexVJANUxmJNl1ooUONVXS | 192.168.40.189 | evidence/attack-mcp-tool-verify/mcp-08.md | 2026-11-15T17:53:31+08:00 | 有效 | — |
| L-3 | 凭据 | dvaa-internal-api-key-abcdef（HelperBot 系统提示内置） | 192.168.40.183:7002 | evidence/verification/dvaa-attack-lab/raw/api-fast.json | 2026-11-25T21:14:00+08:00 | 有效 | 服务端 verify=L1-01 通过；回显一致 |
| L-4 | 凭据 | sk-dvaa-openai-test-key-do-not-use-in-production-12345 | 192.168.40.183:7003 | evidence/verification/dvaa-attack-lab/raw/api-fast.json | 2026-11-25T21:14:00+08:00 | 有效 | 服务端 verify=L1-02 通过；回显一致 |
| L-5 | 凭据 | dvaa-admin-secret（记忆库 admin 口令） | 192.168.40.183:7007 | evidence/verification/dvaa-attack-lab/raw/api-memory.json | 2026-11-25T21:20:00+08:00 | 有效 | 服务端 verify=L2-05 通过；RAG 检索独立复现（L3-01） |
| L-6 | 凭据 | OPENAI_API_KEY=sk-dvaa-demo-openai-key-leaked-via-env / DATABASE_URL=postgres://admin:dvaa-db-password-123@… | 192.168.40.183:7010 | evidence/verification/dvaa-attack-lab/raw/mcp-face.json | 2026-11-25T21:16:00+08:00 | 有效 | 服务端 verify=L3-06 通过；`read_file .env` 回显 |
| L-7 | 系统文件 | /etc/passwd（root/agent/postgres 账户行） | 192.168.40.183:7010 | evidence/verification/dvaa-attack-lab/raw/mcp-face.json | 2026-11-25T21:16:00+08:00 | 有效 | 服务端 verify=L2-03 通过；`root:x:0:0` 回显 |
| L-8 | 内部情报 | legacybot `/info` 完整画像（含 securityLevel、vulnerabilities） | 192.168.40.183:7010 | evidence/verification/dvaa-attack-lab/raw/mcp-face.json | 2026-11-25T21:16:00+08:00 | 有效 | 服务端 verify=L3-02 通过；SSRF 经 `fetch_url` 取得 |

## 攻击路径

<!-- 每完成一段攻击路径追加一行：- 入口 A → B（trad-04 flag）→ C（trad-07 flag） -->
- 入口 http://192.168.40.189 (AIVP) → MCP_01 工具滥用（mcp-05/mcp-07 完全生效）→ 凭据泄露 flag（mcp-08 面板校验 success=True）
