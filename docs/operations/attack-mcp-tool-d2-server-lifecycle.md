# D-2 修复方案：MCP server 生命周期与端口独占

- 上游缺陷：`docs/operations/mcp-service-deep-test-20261126.md` §8 D-2（中危）
- 影响模块：`tools/attack_mcp_tool/poison.py`、`tools/attack_mcp_tool/runner.py`
- 状态：方案待评审（未落代码）

## 1. 结论

**推荐组合方案 B + C，以 A 为前置。** 单点幂等（A）只能消除「二次 start」的调用路径，无法阻止第三方进程与我们的 server 同端口并存；Windows 上 `allow_reuse_address=True` 等价于把监听端口交给任何人复用，属可被本地对手利用的欺骗面。三者组合后：

1. `start()` 幂等，二次调用不产生新监听；
2. `Runtime.server` 所有权显式化，runner 只启动/关闭自己创建的实例；
3. Windows 改用 `SO_EXCLUSIVEADDRUSE`，同端口二次绑定返回 `OSError`，`mcp-02` 的降级分支由死代码恢复为有效路径。

原先担心的代价（`stop()` 后 `TIME_WAIT` 导致端口不可复用）已由本机 spike 否定：独占模式下无论有无流量，重绑均在 1–2 ms 内成功（§2.3）。该结论仍须由 T6 固化为用例，避免换 Windows 版本后静默退化。

## 2. 缺陷事实

### 2.1 已实测（Windows 11 / Python 3.13.14）

| 观测 | 结果 |
|---|---|
| `s1 = PoisonedMcpServer().start()`；`s2 = PoisonedMcpServer(port=s1.port).start()` | 两个 listener 同端口并存，`s2.port == s1.port` |
| 对 `s1.port` 连续 5 次 `GET /tools/list` | 全部 200，未出现绑定错误 |
| `s2.stop()` 后再 `stop()` 全链路 | `s1` 的监听套接字已被覆盖，无法通过 `s2` 关闭 |
| `_Session.ensure_server()` 收到已启动实例 | 再次调用 `start()`，旧 `ThreadingHTTPServer` 对象被丢弃 |
| 端口被占用后由后续进程绑定同端口 | `WinError 10048`（需显式 `SO_EXCLUSIVEADDRUSE` 或关闭复用才报错） |

### 2.2 依据语义、本机未实测（待 CI 验证）

- POSIX 下 `SO_REUSEADDR` 允许绑定处于 `TIME_WAIT` 的端口，但**不允许**与活跃 listener 共用端口（后者需 `SO_REUSEPORT`）。因此 Linux 上二次绑定预期抛 `OSError(EADDRINUSE)`。
- 由此可推：`mcp-02` 依赖 `OSError` 的「本地端口不可用」降级分支在 Linux 上有效、在 Windows 上失效——跨平台行为不一致，但**尚未在 Linux 实跑**。

### 2.3 方案 C spike 实测（Windows 11 / Python 3.13.14，2026-11-26）

| 配置 | 无流量重绑 | 有流量（5 次请求）后重绑 | 同端口二次监听 |
|---|---|---|---|
| `SO_EXCLUSIVEADDRUSE`（方案 C） | 成功，0.001 s | 成功，0.001 s | **失败**（`WinError 10048`） |
| `allow_reuse_address=True`（现状） | 成功，0.001 s | 成功，0.002 s | **成功**（劫持面存在） |

结论：独占地址在达成安全目标（阻断二次监听）的同时**未**引入重绑延迟；`TIME_WAIT` 顾虑在本平台未复现。残余不确定性：spike 使用 HTTP/1.0 短连接（`BaseHTTPRequestHandler` 默认，连接即关），长连接/高并发场景需由 T6 覆盖。

## 3. 根因分解

| 层 | 位置 | 问题 |
|---|---|---|
| L1 生命周期 | `poison.PoisonedMcpServer.start()` | 无幂等守卫，重复调用覆盖 `_server` 并新建线程 |
| L2 所有权 | `runner._Session.ensure_server()` / `close()` | 无条件 `start()`；对注入实例既启动又关闭，所有权未定义 |
| L3 套接字 | `ThreadingHTTPServer.allow_reuse_address = 1` | Windows 语义下允许同端口复用，端口可被第三方劫持 |

L1 是直接诱因，L3 是风险放大器；只修 L1 会让 L3 的劫持面继续存在。

## 4. 方案对比

### 方案 A — 最小幂等守卫

```python
def start(self):
    if self._server is not None:
        return self
    ...
```

- 改动：`poison.py` 3 行。
- 消除：重复 `start()` 造成的对象覆盖与线程泄漏。
- 不消除：第三方进程同端口监听；runner 对注入实例的所有权歧义。
- 回归面：最小；`stop()` 幂等已成立。
- 判定：**必要但不充分**，作为 B/C 的前置。

### 方案 B — 幂等 + 所有权契约

- 新增只读属性 `is_running`（`_server` 非空且 `_thread.is_alive()`）。
- `Runtime.server` 契约改写为「谁启动谁负责关闭」：

| 注入形态 | runner 启动 | runner 关闭 |
|---|---|---|
| `Runtime.server=None`（自建） | 是 | 是 |
| 注入未启动实例 | 是 | 是 |
| 注入已启动实例 | 否 | 否（由注入方 stop） |

- `_Session` 增加 `_owns_server` 标志，`close()` 仅在自己启动时 `stop()`。
- 改动：`runner.py` 约 12 行。
- 消除：注入已启动实例被二次 start、被 runner 意外关闭（当前会把调用方仍在用的 server 停掉）。
- 不消除：端口复用劫持面。
- 兼容性：现有测试无固定端口、无生产代码注入 `Runtime.server`（仅测试注入 `BusyServer`），影响面窄。

### 方案 C — 地址独占加固

```python
class _BoundServer(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = os.name != "nt"   # Windows 关闭复用

    def server_bind(self):
        if os.name == "nt":
            self.socket.setsockopt(
                socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
        super().server_bind()
```

- 效果：Windows 上同端口第二次 `bind` 失败 → `OSError`；`mcp-02` 降级分支恢复有效；POSIX 行为不变。
- 风险：Windows 上 `stop()` 后理论上可能因 `TIME_WAIT` 导致重建监听失败。本机 spike 未复现（§2.3，重绑 1 ms 成功），但仍须由 T6 以长连接场景固化验证。
- 备选 C′：`allow_reuse_address = False`（全平台）。更简单，但在 Windows 上同样受 `TIME_WAIT` 影响，且改变 POSIX 的快速重绑行为，不如 C 精准。
- 已否决的 D：`bind` 前用临时 socket 预探测端口可用性。存在 TOCTOU，且额外占用端口，不能作为安全保证。

## 5. 推荐路线与取舍

1. **先 A 后 B 再 C**，三个独立提交，每步全量回归；任一步失败可单独回滚。
2. 不选「只做 A」：它把问题从「静默双绑定 + 泄漏」降级为「静默不报错」，但同端口仍可被第三方监听，而 `mcp-02` 的降级契约在 Windows 上依旧是死代码。
3. 不选「A + C」跳过 B：注入已启动实例的场景仍会被 runner 二次 `start()`，C 会让这次 `start()` 抛 `OSError`，反而把「静默错误」变成「注入即失败」，比现状更难用。
4. C 的平台差异**已由 spike 初步判定为可接受**（§2.3）；T6 仍须覆盖长连接/高并发，若届时出现重绑失败，优先方案是测试侧重试退避 + 文档标注，而不是回退到 `allow_reuse_address=True`。

## 6. 契约变更

| 契约 | 现状 | 变更后 | 破坏性 |
|---|---|---|---|
| `start()` | 重复调用产生新监听 | 幂等，返回自身 | 否（收紧语义） |
| `stop()` | 幂等 | 不变 | 否 |
| `is_running` | 不存在 | 新增只读属性 | 否（新增） |
| `Runtime.server` | 未定义所有权 | 「谁启动谁关闭」 | 是（对依赖隐式关闭的调用方） |
| `url` 未启动时 | 返回 `:0/mcp` 占位 | 不变，文档标注须先 `start()` | 否 |

`url` 语义刻意不改：`_step_mcp_03` 等处依赖 `started_server.url`，改为抛异常会扩大影响面。

## 7. 测试计划

| 编号 | 用例 | 断言 | 平台 |
|---|---|---|---|
| T1 | `start()` 幂等 | 端口不变、`is_running` 为真、`_thread` 对象身份不变 | 全平台 |
| T2 | 同端口二次绑定 | 抛 `OSError`，且首个 server 仍在服务 | 全平台（Windows 为本次修复目标） |
| T3 | 注入已启动实例 | runner 不再 `start()`；运行后该实例仍可服务、端口未释放 | 全平台 |
| T4 | 注入未启动实例 | 运行结束后端口可立即重绑（runner 已 stop） | 全平台 |
| T5 | `mcp-02` 端口冲突降级 | 等级「已跳过」，reason 含「端口」 | 全平台 |
| T6 | `stop()` 后重绑 | 关闭后立即重绑的成功率与最大等待时长（量化 `TIME_WAIT` 影响） | Windows 重点 |
| T7 | 既有回归 | 全量 1684 例全绿，`attack-mcp-tool` 覆盖率不低于 94.4% | 全平台 |

T2/T6 在现有 `--target attack-mcp-tool` 覆盖范围内，新增用例计入 manifest 的 `tests` 列表。

## 8. 实施步骤

1. **提交 1（A）**：`poison.start()` 幂等；新增 T1。
2. **提交 2（B）**：`is_running` + `_Session._owns_server`；改写 `ensure_server/close`；新增 T3/T4，调整依赖「隐式关闭注入实例」的夹具。
3. **提交 3（C）**：`_BoundServer` 与 Windows 独占地址；新增 T2/T6；`mcp-02` 降级用例 T5 复验。
4. 每步跑：`unittest discover`、`measure_coverage --target attack-mcp-tool --min 90`、`check_tools_compile.py`、`check_glossary.py`。
5. Linux 行为（`EADDRINUSE`）由上表 T2 在 CI（ubuntu-24.04 / Python 3.11）自然验证，不在本机伪造结论。

## 9. 风险与不修的影响

| 风险 | 等级 | 缓解 |
|---|---|---|
| Windows `TIME_WAIT` 导致重绑失败 | 低（spike 未复现） | T6 以长连接/高并发复验；失败时重试退避 + 文档标注，不放宽独占 |
| 所有权契约变更影响未知调用方 | 低 | 仓库内无生产注入；契约写进 `poison.py` 模块 docstring |
| 平台差异导致测试在 CI 上不稳定 | 中 | T2 断言 `OSError` 而非具体错误码；T6 允许退避 |
| 不修 | — | 本机任意进程可与「恶意 MCP server」同端口并存并可截获 JSON-RPC 交互；`mcp-02` 的端口失败降级在 Windows 上恒不触发，演练时无法如实记录「端口不可用」 |

## 10. 验收清单

- [ ] 同端口二次绑定抛 `OSError`（Windows 实测、Linux 由 CI 验证）
- [ ] `start()` 幂等：端口、线程、套接字三者均不新增
- [ ] 注入已启动实例：runner 不启动、不关闭
- [ ] 注入未启动实例：运行后端口可重绑
- [ ] `mcp-02` 端口冲突仍判「已跳过」
- [ ] 全量回归全绿；`attack-mcp-tool` 覆盖率 ≥ 94.4%
- [ ] `poison.py` 模块 docstring 增补所有权与平台差异说明

## 11. 下一步

建议按提交 1/2/3 拆三个工单，或合并为一个工单分三次提交。需要时可直接基于本方案出补丁与用例，无需再次设计。

## 12. 设计记录（主线阶段 6）

### 12.1 模块职责与依赖方向

| 模块 | 职责 | 依赖 |
|---|---|---|
| `poison.PoisonedMcpServer` | 持有监听资源、启停、平台绑定策略、可观测状态 | 仅标准库 `socket` / `http.server` / `threading` |
| `runner._Session` | 决定是否启动、记录归属、在 `finally` 关闭自有实例 | `poison` 单向 |
| `runner._step_mcp_02` | 把启动失败翻译为「已跳过」并附依据 | `_Session` |

依赖方向单向：`runner → poison → stdlib`，无反向引用；本变更新增 seam 数为 0（沿用传输 / 证据写入 / 截图三缝）。

### 12.2 公开接口与错误行为

| 接口 | 输入 | 输出 | 错误行为 |
|---|---|---|---|
| `start()` | — | `self`（幂等） | 端口不可用时抛 `OSError`，不创建部分状态 |
| `stop()` | — | `None` | 不抛异常；未启动/重复调用为空操作 |
| `is_running` | — | `bool` | 不抛异常 |
| `url` | — | `str` | 未启动返回占位端口 0，不改语义 |
| `_Session.ensure_server()` | — | 就绪实例 | 启动失败向上抛，由 mcp-02 捕获 |
| `_Session.close()` | — | `None` | 只关闭自有实例；不自有的实例保持运行 |

对象图收敛位置：`_Session`（唯一持有 `started_server` 与归属标志的地方），`poison` 不感知编排层。

### 12.3 术语映射（阶段 7）

| 概念 | 代码标识符 | 规格条目 |
|---|---|---|
| 监听所有权 | `_Session._owns_server` | US-3/US-4、AC-04 |
| 地址独占 | 平台绑定策略（`allow_reuse_address` / `SO_EXCLUSIVEADDRUSE`） | US-7、AC-03 |
| 运行状态 | `PoisonedMcpServer.is_running` | US-2、AC-02 |

**GLOSSARY 不新增条目**：上述三词仅进入实现与工程规格，未进入 `SKILL.md` 与报告口径（D-4 不在本次范围）；且 `GLOSSARY.md` 已达 22,715B / 上限 23,000B（余量 285B），按 C4 不挤占空间。若后续 SKILL.md 引入这些词，须先压缩既有条目再补录。
