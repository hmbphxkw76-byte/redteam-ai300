# MCP server 生命周期与端口语义调研（Winsock / POSIX / CPython）

- 阶段：主线阶段 1 `research`（变更域：D-2 服务生命周期与端口独占）
- 核实日期：2026-11-26
- 一手源：MS Learn Winsock 文档、Linux man-pages 6.19 `socket(7)`、CPython 3.13.12 标准库源码、Python 3.15 文档、本机实测

## 1. 已核实结论

| # | 结论 | 来源 |
|---|---|---|
| R-1 | Windows 的 `SO_REUSEADDR` **允许第二个 socket 强制绑定到已被占用的端口**，且「绑定成功后该端口所有 socket 的行为不确定」，端口劫持无需特权 | MS Learn《Using SO_REUSEADDR and SO_EXCLUSIVEADDRUSE》 |
| R-2 | Windows 服务器必须设 `SO_EXCLUSIVEADDRUSE`；否则「应用必须视为不安全」。首个 socket 用独占地址绑到同一端口时，后续 bind 返回 `WSAEADDRINUSE` 或 `WSAEACCES` | 同上 |
| R-3 | 独占地址模式下「socket 关闭后**不必然**可立即复用」，需原连接转为非活动；官方建议优雅关闭（`shutdown(SD_SEND)` + `recv` 至 0 字节），不推荐 `SO_LINGER` | 同上 |
| R-4 | Linux 的 `SO_REUSEADDR` **不允许**与活跃 listener 共用端口：「a socket may bind, **except when there is an active listening socket bound to the address**」；同端口并发监听需 `SO_REUSEPORT`（Linux 3.9+，且要求所有 socket 同 eUID） | Linux man-pages 6.19，`socket(7)`，2026-06-05 |
| R-5 | CPython `TCPServer.allow_reuse_address` 默认 `False`；`server_bind()` 仅在为真时 `setsockopt(SO_REUSEADDR, 1)` | CPython 3.13.12 `Lib/socketserver.py` L446、L463–470 |
| R-6 | `http.server.HTTPServer` 将 `allow_reuse_address` 覆写为 `1`，源码注释为「Seems to make sense in testing environment」；`ThreadingHTTPServer` 继承该值并设 `daemon_threads = True` | CPython 3.13.12 `Lib/http/server.py` L134–148 |
| R-7 | `TCPServer.request_queue_size` 默认 5；Python 3.15 起改为 `socket.SOMAXCONN` | CPython 源码 L444；Python 3.15 文档 `socketserver` |
| R-8 | 本机 Windows 11 / Py 3.13.14 实测：独占地址下同端口二次 bind 抛 `WinError 10048`；关闭后重绑（含 5 次请求后）均在 1–2 ms 成功；现行 `allow_reuse_address=True` 下二次 bind 成功 | 本仓 `evidence/mcp-deep-test/d2_spike.py` 输出 |

R-3 与 R-8 存在表观张力：官方只承诺「不必然可复用」，本机场景（HTTP/1.0 短连接、listener 无存活连接）未触发该限制。二者不矛盾——R-3 描述上限，R-8 是特定场景的下界观测。

## 2. 待核实（带取证方式）

| # | 事项 | 取证方式 | 状态 |
|---|---|---|---|
| U-1 | Linux 上同端口二次 bind 的实际错误码（`EADDRINUSE`）与异常类型 | CI（ubuntu-24.04 / Python 3.11）跑 T2；本机无 Linux 环境 | 待 CI |
| U-2 | 独占地址在长连接 / 高并发后的重绑延迟 | T6 用例：keep-alive 请求 50 次后再 `stop()` 重绑，记录耗时与失败率 | 待实施 |
| U-3 | eUID 不同时 Linux 的 `SO_REUSEADDR` 行为差异是否影响本仓（单进程、同用户） | 不适用：本仓 server 与客户端同进程同用户 | 已排除影响 |

## 3. 已排除

- **E-1**：用「先 bind 一个临时 socket 探测端口是否空闲」作为安全判定。MS Learn 明确指出劫持无需特权且行为不确定，探测与真正 bind 之间存在 TOCTOU，不能替代独占地址。
- **E-2**：改用 `SO_REUSEPORT` 规避。该选项的用途是**允许多监听者**，与本文目标（禁止他者监听）相反。
- **E-3**：依赖 `server_version` 或应用层 token 区分敌我。端口已被他者持有时，连接可能被任一方接收，应用层无法保证。

## 4. 对象映射（SKILL.md 步骤 → 代码对象）

| SKILL.md | 代码对象 | 本变更影响 |
|---|---|---|
| mcp-02 部署恶意 MCP server | `poison.PoisonedMcpServer`（`start/stop/url`）、`runner._Session.ensure_server/close` | 生命周期与所有权契约 |
| mcp-03/04 工具面与差分 | `poison.baseline_surface/poisoned_surface/diff_*` | 不受影响 |
| 证据落盘 | `EvidenceWriter`（委托 `collect_evidence.py`） | 不受影响 |

## 5. 对规格阶段的输入

1. 规格必须区分「谁拥有监听」（B）与「监听是否可被他人共享」（C）两个独立要求，不可合并为「端口冲突处理」一条。
2. 规格不得承诺「关闭后必然立即可重绑」——官方只保证「不必然」，因此验收条件应表述为「重绑在给定退避窗口内成功」，而非「立即成功」。
3. 平台差异属规格级约束：Windows 依赖 `SO_EXCLUSIVEADDRUSE`，POSIX 依赖「不设 `SO_REUSEPORT`」即可满足独占。
