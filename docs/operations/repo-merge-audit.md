# 仓库合并与数据完整性审计

> **日期** 2026-11-24 · **性质** 会话合并留痕
> **范围** 12 个 worktree 活跃分支；不合并 `backup/*` 与历史废弃分支；不删除 worktree。

## 1. 数据完整性证明（写操作前）

两份 Ch8 文档在 main 工作树为 untracked；与远端备份分支 `origin-https/backup/untracked-ch8-docs-20261122` 同名 blob 逐字节比对：

| 文件 | 本地 SHA-256 | 备份 blob SHA-256 | 判定 |
|---|---|---|---|
| `docs/research/attack-supply-chain-ch8-gap.md` | `27867f1aa76537a05417cb6b2c9bc9061bd2ee389ab69400a676e3b9d1503c0d` | `27867f1aa76537a05417cb6b2c9bc9061bd2ee389ab69400a676e3b9d1503c0d` | 一致 |
| `docs/research/attack-supply-chain-ch8-mainline-prompt.md` | `79bf79afea7e8f6d56739a1c4994b7899d84ffcedd55e4b79997679ae87d518d` | `79bf79afea7e8f6d56739a1c4994b7899d84ffcedd55e4b79997679ae87d518d` | 一致 |

结论：两份文档零丢失，备份可恢复；提交前基线 HEAD `4f5cd9ef7b6e215c0c3e1b2e66ae7dc2c277a098`。

## 2. Worktree 会话清单（合并前）

`behind/ahead` 相对 `origin/main`；`ahead=0` 表示内容已合入 main。

| Worktree | 分支 | behind/ahead | HEAD | 处置 |
|---|---|---|---|---|
| `D:/文档/GitHub/redteam-ai300` | `main` | 0/0 | `4f5cd9ef` | 目标分支 |
| `D:/_attack-ai-agent-ch3_wt` | `feat/attack-ai-agent-ch3-alignment` | 54/0 | `bfdc24cd` | 已合入 |
| `D:/_attack-embeddings_wt` | `feat/attack-embeddings` | 52/0 | `5c2fd64b` | 已合入 |
| `D:/_attack-infra_wt` | `feat/attack-infra` | 100/0 | `7c882c1e` | 已合入 |
| `D:/_attack-mcp-tool_wt` | `feat/attack-mcp-tool` | 31/0 | `38a8599f` | 已合入 |
| `D:/_attack-rag-ch6_wt` | `feat/attack-rag-ch6` | 52/0 | `d5878cd8` | 已合入 |
| `D:/_ci-cleanup_wt` | `feat/ci-cleanup` | 61/0 | `8ff8b004` | 已合入 |
| `D:/_contract-drift-prevention_wt` | `feat/contract-drift-prevention` | 105/0 | `c1fca6a4` | 已合入 |
| `D:/_pyrit-compat_wt` | `feat/pyrit-compat` | 2/1 | `e3232ae5` | PR #440 待合并 |
| `D:/_recon-ai-ch2_wt` | `feat/recon-ai-ch2` | 39/0 | `d538751d` | 已合入 |
| `D:/_recon-ai_wt` | `feat/recon-ai` | 95/0 | `22a55bbe` | 已合入 |
| `D:/_sc_tools_wt` | `feat/attack-supply-chain-tools` | 103/0 | `51a54b41` | 已合入 |

排除项：`backup/*` 与历史 `feat/*`（pre-rebase 备份、废弃尝试）非活跃会话，不合并、不删除。

## 3. 合并与推送记录

1. PR #440 首次 squash 合并被拒（not mergeable，branch 落后 main 2 commit）。按最佳实践在 `D:/_pyrit-compat_wt` 执行 `git fetch origin main` + `git merge origin/main`；冲突仅发生在两个共享文件：`scripts/measure_coverage.py`（`ALL_TARGET_ORDER`）与 `scripts/tools_manifest.json`（`coverage_targets` 末段）。按 ADR-0006 取双方并集：`attack-jailbreak`、`attack-multimodal`、`pyrit-compat` 三项全保留。
2. 冲突解决后复跑门禁：编译 259 文件失败 0、契约清单/消费者/预算/检出锁 PASS、`validate_skill`/`check_glossary`/`check_evidence_contract` PASS、全量测试 1312 例 OK（3 skipped）、`pyrit-compat` 覆盖率 84.4%。
3. 冲突解决提交 `8bde5ea`，SSH 推送 `feat/pyrit-compat` 成功；PR CI 复跑 S1/S2/AC-12 全 PASS（S3/S4 按配置 skipping）。
4. `gh pr merge 440 --squash` 成功；PR #440 状态 `MERGED`，合并提交 `53721624e8279d778898afde31ca19f4afdd73cd`。
5. main 工作区 `git merge --ff-only origin/main` 至 `5372162`，两份 Ch8 文档与审计文件仍为 untracked，无覆盖或丢失。

## 4. 收尾验证

待执行。
