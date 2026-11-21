# attack-mcp-tool Ch7 增量 — 阶段11 pre-push-review

> **基线** `git merge-base origin/main HEAD` = 8db9bc3（已 rebase 到最新 origin/main）
> **领先提交** 8 · **diff** 15 文件 +935/-6 行
> **性质** 阶段 11 复合阶段第 1 步：推送前语义级双轴评审 + 门禁套件

## 1. pre-push-review 双轴结论

| 轴 | 发现数 | 最严重项 | 分类 | 结论 |
|---|---|---|---|---|
| Standards | 0（新增） | 无 | 阶段10已清零（见 `attack-mcp-tool-ch7-gap-code-review.md`） | PASS |
| Spec | 0（新增） | 无 | 阶段10已清零；rebase 后增量仅为共享文件自动合并 | PASS |

rebase 后未引入新代码变更，仅共享文件（GLOSSARY/manifest）按 git 三方合并自动取并集；阶段10双轴报告结论沿用并经门禁复跑确认。

## 2. 门禁套件（结果行 passed）

| 检查 | 命令 | 结果 |
|---|---|---|
| 技能结构 | `python scripts/validate_skill.py` | passed（16 技能） |
| 术语 | `python scripts/check_glossary.py` | passed（64 废弃术语） |
| 证据契约 | `python scripts/check_evidence_contract.py` | passed（4 适配器） |
| 单元测试 | `python -m unittest discover -s tests/attack_mcp_tool -t .` | passed（81 OK） |
| 覆盖率 | `python scripts/measure_coverage.py --target attack-mcp-tool --min 80` | passed（81.4%） |
| Token 预算 | `python scripts/check_token_budget.py --check` | passed |

## 3. 推送前共享文件并集确认

| 文件 | 状态 | 确认 |
|---|---|---|
| GLOSSARY.md | 我的 5 个 MCP 术语 + 远端 3 个 embedding 术语共存 | 逐条 grep 计数=1，通过 |
| scripts/tools_manifest.json | 远端改 embeddings/rag 条目；本次待注册 attack-mcp-tool 新模块（串行合并处理） | 位置不重叠 |
| 检出锁 | `checkout_lock.py --check` 报 `_recon-ai-ch6_wt` 并发改 GLOSSARY | 对方分支未合入 main，其 GLOSSARY 改动为陈旧删除（基于旧基线删除 main 已有术语），方向与 main 相反 |

## 4. 推送要素

- PR 正文：`attack-mcp-tool-ch7-gap-pr-body.md`（1994/3000 B，C4 PASS）
- 目标分支：`feat/attack-mcp-tool` → `main`（经 PR 合并）
- 推送通道：SSH `origin` → HTTPS `origin-https`，各试一次即停
- 检出锁：如阻断，按规范停留本阶段，不以 `--no-verify` 绕过（除非人工确认并集无误）
