# 仓库无效引用清理审计

> **日期** 2026-11-24 · **性质** S0 破坏性操作留痕
> **范围** 仅删除已合入 main 或 PR 已 MERGED 且合并后无新提交的 worktree 与分支引用；保留全部 `backup/*`、tag、无 PR 分支与治理资产。

## 1. 删除前快照

- main HEAD：`df4954c479722a4597bd1f0da64777fb2a02d6fd`，本地与 `origin/main` 一致，工作树 clean。
- worktree 数：12（含主 worktree）；本地分支数：67；远端唯一分支名：64（origin 与 origin-https 双份）；MERGED PR：500 上限内全部拉取；tag 2 个；stash 空。
- 证据方法：① `git branch --merged origin/main` 判定祖先关系；② `gh pr list --state merged` 取 `mergedAt`，再用 `git log --format=%H%x09%cI origin/main..<branch>` 按正确时区解析比对，合并时刻之后仍有提交的分支判为 BLOCKED 保留。

## 2. 删除集合（S0）

### 2.1 worktree（11 个，均 clean 且内容已合入 main）

`D:/_attack-ai-agent-ch3_wt`、`D:/_attack-embeddings_wt`、`D:/_attack-infra_wt`、`D:/_attack-mcp-tool_wt`、`D:/_attack-rag-ch6_wt`、`D:/_ci-cleanup_wt`、`D:/_contract-drift-prevention_wt`、`D:/_pyrit-compat_wt`、`D:/_recon-ai-ch2_wt`、`D:/_recon-ai_wt`、`D:/_sc_tools_wt`。

### 2.2 本地分支（38 个）

祖先证据（15 个）：`chore/tooling-automate-finalize`、`docs/ai-range-target-selection`、`feat/attack-ai-agent-ch3-alignment`、`feat/attack-embeddings`、`feat/attack-embeddings-tools`、`feat/attack-infra`、`feat/attack-ma-regression-verify`、`feat/attack-mcp-tool`、`feat/attack-rag-ch6`、`feat/attack-supply-chain-tools`、`feat/audit-align-fix`、`feat/ci-cleanup`、`feat/contract-drift-prevention`、`feat/framework-docs-recovery`、`feat/recon-ai`、`feat/recon-ai-ch2`。

MERGED PR 证据（23 个）：`docs/repo-cleanup-audit` #409、`feat/a2a-ch4-mainline` #311、`feat/align-partial` #270、`feat/asc-ch9-b6-hardening` #384、`feat/attack-infra-ch9` #354、`feat/attack-jailbreak` #432、`feat/attack-multimodal` #439、`feat/attack-rag-ch3-alignment` #323、`feat/attack-supply-chain-ch9` #363、`feat/foothold-traditional-ch9` #357、`feat/foothold-traditional-ch9-hardening` #377、`feat/loot-manage-b5-hardening` #391、`feat/loot-manage-ch9` #360、`feat/pyrit-compat` #440、`feat/recon-ai-c1-hardening` #399、`feat/recon-ai-ch6-resolve` #408、`feat/recon-ai-ch9` #366、`feat/stage-manifest-test-paths` #269、`feat/tests-reorg` #268、`feat/threat-model-ch10` #335、`feat/threat-model-ch9` #369、`feat/tm-c3-hardening` #407、`feat/verify-evidence` #?（远端专属）。

### 2.3 远端分支（50 个唯一名，origin 与 origin-https 同一仓库只删一次）

`chore/tooling-automate-finalize`、`docs/repo-cleanup-audit`、`docs/verify-evidence-align-fix`、`docs/verify-evidence-gate11`、`feat/a2a-ch4-mainline`、`feat/align-partial`、`feat/asc-ch9-b6-hardening`、`feat/attack-ai-agent`、`feat/attack-ai-agent-ch3-alignment`、`feat/attack-embeddings`、`feat/attack-embeddings-tools`、`feat/attack-infra`、`feat/attack-infra-ch9`、`feat/attack-jailbreak`、`feat/attack-mcp-tool`、`feat/attack-multi-agent-glossary`、`feat/attack-multimodal`、`feat/attack-rag`、`feat/attack-rag-ch3-alignment`、`feat/attack-rag-ch6`、`feat/attack-supply-chain`、`feat/attack-supply-chain-ch11-integrity`、`feat/attack-supply-chain-ch9`、`feat/attack-supply-chain-tools`、`feat/audit-align-fix`、`feat/capstone-rehearse`、`feat/ci-cleanup`、`feat/contract-drift-prevention`、`feat/contract-hashfix`、`feat/foothold-traditional`、`feat/foothold-traditional-ch9`、`feat/foothold-traditional-ch9-hardening`、`feat/framework-docs-recovery`、`feat/loot-manage`、`feat/loot-manage-b5-hardening`、`feat/loot-manage-ch9`、`feat/loot-manage-skill-parity`、`feat/pyrit-compat`、`feat/recon-ai`、`feat/recon-ai-c1-hardening`、`feat/recon-ai-ch2`、`feat/recon-ai-ch6-resolve`、`feat/recon-ai-ch9`、`feat/stage-manifest-test-paths`、`feat/tests-reorg`、`feat/threat-model-ch10`、`feat/threat-model-ch9`、`feat/tm-c3-hardening`、`feat/tooling-automate`、`feat/verify-evidence`。

## 3. BLOCKED（合并后仍有新提交，保留）

本地与远端均为：`feat/verify-evidence-225`（`1c9742e1`）、`feat/verify-evidence-dual`（`28cdd6b3`）、`feat/verify-evidence-records`（`7e90bc6c`）。这三组提交时间晚于 PR mergedAt，属于合并后新增工作，不得删除，待人工判定。

## 4. 明确保留（S2）

`main`；全部 `backup/*` 分支与 tag `backup/attack-rag-archive-20261115`、`backup/ch2-pre-merge-20261122-004518`；无 MERGED PR 的 `feat/a2a-ch4-alignment`、`feat/recon-ai-ch6`、`docs/ai-range-target-selection`、`fix/report-image-path-relative`、`wip/archive-orphans`；`.workbuddy/`、hooks、reflog、所有 stash。

## 5. 执行与验证结果

待执行。
