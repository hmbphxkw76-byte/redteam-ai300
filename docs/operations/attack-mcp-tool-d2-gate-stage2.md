# 阶段 2 门禁记录 — to-spec ①

> 变更域：D-2 服务生命周期与端口独占；规格 issue #464。

- **变更项**：行为规格 v1，落 `docs/specs/attack-mcp-tool-d2-spec-v1.md` 并发布 issue #464；七节齐全，US-1…US-10 覆盖幂等/所有权/独占/降级。
- **判定**：PASS（无文件路径与代码片段；seam 结论=新增 0，已在 D-2 评审时核对）。
- **复验**：`gh issue view 464 --json body --jq '.body | length'`；本地文件 2.9KB（≤8KB）。
- **结论**：What 层完整，未混入实现细节。
