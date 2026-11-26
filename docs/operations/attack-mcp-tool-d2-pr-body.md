# fix(attack-mcp-tool): D-2 服务生命周期与端口独占

## Summary

- 能力域：D7 MCP 与工具面滥用（`attack-mcp-tool`）；优先级 P0；计分单元 AI向量机
- 端到端演示：`cli.py --mode jsonrpc --path A..F` 对本地对照组落盘 11/11 证据片段
- 三个可独立回退的修复：

```
PoisonedMcpServer.start()        A  幂等 + is_running
        │
        ├── _Session.ensure_server    B  谁启动谁关闭
        │
        └── _PortExclusiveServer      C  Windows 独占地址
```

## Evidence

| 场景 | 改前 | 改后 |
|---|---|---|
| 同端口二次监听 | 成功（劫持面） | `OSError`（AC-03） |
| 注入已启动实例 | 被编排层关闭 | 保持运行（AC-04） |
| 未注入 | 自建自关，无断言 | 自建自关 + 端口释放（AC-06） |
| 端口冲突时 mcp-02 | Windows 不触发降级 | 真实冲突判「已跳过」（AC-07） |
| 全量回归 | 1684 例 | 1693 例全绿（2 跳过） |
| 覆盖率（门槛 90%） | 94.4% | 94.4% |

- 规格：`docs/specs/attack-mcp-tool-d2-spec-v2.md`（issue #464）
- 工单：#465（A）/ #466（B）/ #467（C）
- 调研：`docs/research/mcp-server-lifecycle-winsock-posix.md`（R-1…R-8，一手源）

## Merge Danger

- **单向门**：C（独占地址）改变端口可用性语义，回退须删提交，不能靠改配置绕过。
- **影响半径**：`poison.py`、`runner.py` 与两个测试文件；不改 `STEP_IDS`、证据格式、公共 API 签名。
- **跨平台**：POSIX 行为不变（`allow_reuse_address` 仍为真）；Linux 的 `EADDRINUSE` 由 CI 自然验证（U-1 未关闭）。
- **回滚**：按 A / B / C / 审查修复四个提交逐个 revert。

Closes #465
Closes #466
Closes #467
