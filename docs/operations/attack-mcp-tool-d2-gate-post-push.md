# 推送后核验记录 — D-2 推送与 CI 复验

> 变更域：D-2；本地 `main` → `origin/main`（SSH 通道）。

## 第 1 次推送（`41a9542`）

- 命令：`git push origin main`；`pre-push-verify` 五项全 OK，共享检出锁 PASS。
- 结果：`084d763..41a9542`，6 个提交。
- CI `45842886688`：S1 success、**S2 failure**、S3/S4 skipped；T06 `45842886693` success。
- S2 失败项：`test_rebind_within_window_after_traffic`，Linux 报
  `OSError: [Errno 98] Address already in use` → 断言「端口未在 2.0s 内释放」。

## 根因

用例探针用裸 `socket.bind`，未设 `SO_REUSEADDR`；50 次请求后内核仍持 TIME_WAIT
条目，2 s 内恒失败。产品重绑路径在 POSIX 已设 `SO_REUSEADDR`（`_PortExclusiveServer`），
本可即时重绑。故属**用例判据错误**：断言严于 AC-05（「组件可重新绑定同一端口」）。

## 修复（`6dff5c8`）

- 新增 `tests/attack_mcp_tool/_ports.py:rebind_within`，复用 `PoisonedMcpServer`
  绑定路径（POSIX `SO_REUSEADDR` / Windows `SO_EXCLUSIVEADDRUSE`），判据与产品一致。
- 两处同形 helper 归一，删除未使用 import。

## 第 2 次推送与结果

- 结果：`41a9542..6dff5c8`；CI `45844286877` 全绿——S1/S2/S3/S4 均 success；T06 `45844287203` success。
- 本地：全量 1693 例 OK（2 跳过）；`attack-mcp-tool` 覆盖率 94.4%（门槛 90%）。
- `git rev-parse origin/main` = `6dff5c8`；工作区干净。

## 判定

- 判定：PASS（远端与本地一致，四道 job 全绿）。
- **U-1 转为已验证**：Linux 上同端口二次监听确抛 `OSError`（`Errno 98`），
  `test_second_listener_on_same_port_is_rejected` 在 CI 通过；原「依据语义、待验证」的标注可撤销。
- 遗留：U-2（长连接后重绑窗口仍以 50 次短连接近似）、D-4（SKILL.md 缺 mcp-09..11）、D-12（主线留痕缺口）。
