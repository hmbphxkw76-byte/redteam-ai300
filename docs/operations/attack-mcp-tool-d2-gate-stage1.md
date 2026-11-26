# 阶段 1 门禁记录 — research

> 变更域：D-2 服务生命周期与端口独占；规格 issue #464。

- **变更项**：新增 `docs/research/mcp-server-lifecycle-winsock-posix.md`；R-1…R-8 标「已核实」并附一手源 URL/版本（MS Learn、Linux man-pages 6.19、CPython 3.13.12 源码、Python 3.15 文档）。
- **待验证**：U-1（Linux `EADDRINUSE`，CI 验证）、U-2（长连接后重绑窗口，T6 覆盖）。
- **判定**：PASS（B7/B8/B9 无缺项）。
- **复验**：`grep -c "^| R-" docs/research/mcp-server-lifecycle-winsock-posix.md` → 8。
- **结论**：每条结论可定位到一手源；版本明确；R-3 与 spike 的表观张力已显式说明。
