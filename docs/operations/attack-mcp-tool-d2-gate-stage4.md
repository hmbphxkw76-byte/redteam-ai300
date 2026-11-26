# 阶段 4 门禁记录 — to-tickets

> 变更域：D-2 服务生命周期与端口独占；规格 issue #464。

- **变更项**：父 #464 = 规格 issue；子工单 A #465、B #466、C #467，`blocked-by` 链 465→466→467，并挂为 #464 子工单。
- **判定**：PASS（每条 AC 至少被一张工单覆盖；无环；每张可单独验收）。
- **复验**：`gh api repos/{owner}/{repo}/issues/466 --jq .issue_dependencies_summary.blocked_by`。
- **结论**：覆盖矩阵无空格。
