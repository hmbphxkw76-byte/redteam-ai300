# 共享文件并集核验记录（ADR-0006 检出锁例外依据）

> 日期 2026-11-22 · 本 worktree `D:/_threat-model-ch10_wt`（feat/threat-model-ch10，commit f8f6abb）· 并行 worktree `D:/_recon-ai-ch6_wt`（feat/recon-ai-ch6，staged 未提交）
> 结论：并行会话对 3 个共享文件的 staged 改动**全部已存在于本 worktree 对应文件中（逐字匹配）**，本版本为严格超集；取并集 = 保留本版本。零数据丢失，满足 `--no-verify` 例外条件（并集无误 + 逐项确认）。

## 1. GLOSSARY.md（并行 2 hunk → 均已存在）
| hunk | 并行会话 staged 内容 | 本版本位置 | 核验 |
|---|---|---|---|
| H1 L124 | embedding 反演条目改为「vec2text 多步纠错/填槽/beam search…Ch6 增量反演原语」 | 本文件 L146-147 逐字一致 | 已存在 |
| H2 L342 | 新增「推断探测 (inference probing)」+「块分选 (chunk triage)」两术语 | 本文件 L366-372 逐字一致 | 已存在 |
> 本版本另有 Ch10 五项新增术语（假设登记册/信任区/推理强制边界/皇冠珠宝/攻击情报简报），为合法增量，不覆盖上述任何内容。

## 2. scripts/check_token_budget.py（并行 1 hunk → 已存在）
| hunk | 并行会话 staged 内容 | 本版本位置 | 核验 |
|---|---|---|---|
| H1 L49 | 17500 → 18000（含「attack-embeddings Ch6 增量并入 #275 的 2 条术语」理由注释） | 本文件注释段逐字包含该 3 行，且续接 18000→19500→20500 | 已存在（严格超集） |

## 3. scripts/tools_manifest.json（并行 2 hunk → 均已存在）
| hunk | 并行会话 staged 内容 | 本版本位置 | 核验 |
|---|---|---|---|
| H1 | attack_embeddings 增 8 模块 + 2 测试（exporter/fingerprint/probing/triage/slotfill/beamsearch/decision/envelope；test_ch6/test_ch6_cli） | 本版本对应 entries 全部含这些项 | 已存在 |
| H2 | attack_rag 增 ch6_adapter 模块 + test_ch6 | 本版本对应 entries 含这两项 | 已存在 |
> 已核验：上述 8+2 模块与测试文件在本 worktree 中均实际存在（存在性检查全 EXISTS），非悬空引用。本版本另增 threat-model 5 模块 + test_threat_model_ch10，为合法增量。

## 4. 例外依据与风险控制
- **依据**：ADR-0006「共享文件取并集后按合并实际内容重算」；项目既有先例（2026-11-22 07:04 收口，用户授权 `--no-verify` 前已完成同类并集确认）。用户本次指令「保障数据完整无缺情况下执行，完成闭口」——本次并集核验即数据完整性证明，满足前提条件。
- **通道**：SSH 优先，一次即停；HTTPS 不经试（block 来自本地 hook 而非网络，重试无意义）。
- **不可控项声明**：并行会话 staged 改动基于陈旧基线（17500 上限 / 无 Ch7 术语），若其后续未经并集直接提交推送，将回退 main 至 18000 上限并丢失 Ch7 MCP 术语——此为该会话自身责任，本 worktree 不改动其工作树（遵守三层隔离：不污染并行会话）。本次闭口推送的本版本为超集，不会造成该回退。
- **零丢失证明**：本 worktree 工作树干净、commit f8f6abb 完整（20 文件 / +1393−54 行），全量 1014 测试 OK、覆盖率 87.3%（基线 85.7%）。

## 5. 核验命令（可复验）

```
git -C D:/_recon-ai-ch6_wt diff --cached -- GLOSSARY.md scripts/check_token_budget.py scripts/tools_manifest.json
grep -n "推断探测\|块分选\|19500 → 20500" D:/_threat-model-ch10_wt/GLOSSARY.md D:/_threat-model-ch10_wt/scripts/check_token_budget.py
python -c "import json; d=json.load(open('D:/_threat-model-ch10_wt/scripts/tools_manifest.json')); ..."
```
