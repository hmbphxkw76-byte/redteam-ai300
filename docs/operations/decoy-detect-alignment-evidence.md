# decoy-detect 对齐审计证据（AC-3 并行数据保护）

> 审计对象：会话 `3b965357-c0ca-4f4d-a81b-34a4515de6a0`（10.decoy-detect-确认）
> 基线：`main @ 5dad10be6c0faa736809385483da8cb39c1e2a67`（2026-11-17）
> 方法：对齐 `docs/operations/verify-evidence-toolchain-audit.md#4` 的「不伪造前指纹、改用等价判据 + 强制留证」范式。

## 1. 缺口与裁决

审计 §3 要求「跨 worktree 操作前后对受影响文件集输出 SHA-256 清单，N/N IDENTICAL」。本会话当时仅留「字节级一致，无发散」文字记载（`.workbuddy/memory/2026-11-15.md#51`），未落盘前置清单；且原始未跟踪状态已随 PR #191 合入 main 而不复存在。按先例 §4，**不伪造历史指纹**，改用当代可复验的等价判据三命题。

## 2. 等价判据三命题（机器取证结果）

| 命题 | 复现命令 | 结果（2026-11-17） |
|---|---|---|
| P1 数据完整性：main blob 与工作树逐字节一致 | Python 读 `git show main:<f>` 与工作树文本，CRLF→LF 归一化后 `sha256` 比对 | **14/14 IDENTICAL**（`git ls-files tools/decoy_detect/ tests/decoy_detect/ tests/fixtures/decoy_scan.json` 全量） |
| P2 他人工作区零写入 | 遍历 `git worktree list` 全部 worktree，`git -C <wt> status --porcelain` | **11 worktree 中 0 个有未提交改动** |
| P3 无删除残留 / 无越权入库 | `git ls-files -o --exclude-standard \| grep -i decoy`；`git log --all -- <旧路径>` 性质复核 | 未跟踪 decoy = **0**；旧路径 log 命中均为 decoy 自身轨迹（#191、557e289、88c48e9/c9242c0 WIP 备份），非他人文件误提交 |

## 3. 跨分支哈希差异定性（A/B）

当代 blob 对比 11 个 worktree 分支为 10/13 一致。对 3 项差异执行 `git merge-base <branch> main` + `git rev-parse <branch>:<file>` / `<merge-base>:<file>` 的 A/B：

- `tools/decoy_detect/evidence.py` 等：各分支版本 == 其**分叉点**版本 → 判定「基线落后」，非本会话引入。
- `tests/decoy_detect/test_*.py` 在部分分支 `git rev-parse` 返回 MISSING → 判定「分叉点早于测试入库」，非删除。

结论：全部差异归因于并行分支分叉点早于本会话合并，属 D8 基线演进；无本会话写入他人 worktree 的证据。

## 4. 强制留证（后续操作规范）

跨 worktree 操作前输出 `sha256sum <files> > <manifest>.before`，操作后输出 `.after` 并 `diff`；受影响文件须同时满足「字节数 == 基线 blob 字节数」与「LF 归一化 SHA-256 == 基线 blob SHA-256」；删除类产物追加 `git log --all -- <path>` 空结果断言。缺前置清单即判取证不足，不得宣称 IDENTICAL（继承 `verify-evidence-toolchain-audit.md#4` 结论）。

## 5. 复验命令汇总

```
python -m unittest discover -s tests/decoy_detect -q     # Ran 59 / OK
python -m unittest discover -s tests -q                  # Ran 891 / OK (skipped=1)
python scripts/measure_coverage.py --target all --min 80 # 89.6% rc=0
python scripts/checkout_lock.py --check                  # rc=0 PASS
python scripts/check_glossary.py                         # PASS (57 废弃术语)
```
