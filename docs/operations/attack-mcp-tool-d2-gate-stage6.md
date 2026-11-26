# 阶段 6 门禁记录 — codebase-design

> 变更域：D-2 服务生命周期与端口独占；规格 issue #464。

- **变更项**：D-2 方案文档新增 §12 设计记录——模块职责与依赖方向、6 个公开接口的输入/输出/错误行为、对象图收敛位置（`_Session`）。
- **判定**：PASS（seam 新增 0；接口错误行为明确；无旧版 PyRIT 对象）。
- **复验**：`sed -n '/## 12/,$p' docs/operations/attack-mcp-tool-d2-server-lifecycle.md`。
- **结论**：接口少、实现深，测试成本可控。
