# attack-rag Ch5 增量端到端验证

> **性质**：阶段 8–11 交付物的可复现验证证据；环境 Python 3.13、标准库、离线 FakeBackend。
> **被测**：`tools/attack_rag/` 新增 7 模块 + `ch5.py`/`ch5_cli.py` + 主链 `runner.py`/`surface.py` 增量；规格 issue #274；PR #308。
> **基线**：`origin/main@831df49`（含 attack-rag v1.1）。

## 1. 语法、测试与覆盖率

```bash
python -m py_compile tools/attack_rag/*.py
python scripts/check_tools_compile.py                       # 181 文件，失败 0
python -m unittest discover -s tests -t . -q                # 915 tests, OK (skipped=3)
python -m unittest discover -s tests/attack_rag -t . -q     # 112 tests, OK
python scripts/measure_coverage.py --target attack-rag --min 80
```

结果：attack-rag 行覆盖率 **1143/1243 = 92.0%**（门槛 80%，exit 0）；反证 mutation 见 §3。

## 2. 四步证据链路（rag-06..09）

```bash
python tools/attack_rag/ch5_cli.py --target rag-ch5 --evidence-dir <dir>
```

| 步骤 | 判定 | 依据 |
|---|---|---|
| rag-06 能力探测与休眠触发 | 完全生效 | 四类能力分类 + 过滤不对称结论 + 休眠文档不含高频查询词 |
| rag-07 规避载荷与上传合规 | 部分生效 | 载荷离线构造完成；upload_manifest 字段待实网回填（不伪造观测） |
| rag-08 信息提取与多主题碰撞 | 完全生效 | three 主题碰撞点；合成命中率 3/4=75% 达阈值 |
| rag-09 融合/慢滴/架构基线 | 部分生效 | 偏移 501 / 预算 600 / 慢滴 Day1..10 / 架构字段；trace_visibility 为静态推断（V-3） |

每步经共享收集器 `--step rag-NN --strict` 落盘（退出码 0），三件套齐全；
`report_exam.index.parse_fragment` 对四片段解析成功（证据契约测试断言）。

## 3. 反证（mutation）

对 `blend.safe_offset()` 返回值注入 `+1`：`test_safe_offset_501` 转红（`502 != 501`）；
恢复后转绿，`git diff` 对 `blend.py` 为空，零残留。

## 4. 门禁与预算

| 编号 | 命令 | 结果 |
|---|---|---|
| B2 | `python scripts/check_glossary.py` | PASS（57 废弃术语） |
| B3 | `python -m py_compile` + `unittest discover` | 915 OK |
| B6 | `python scripts/measure_coverage.py --min 80` | 92.0% |
| B7 | grep 禁用 PyRIT 名 | 无命中 |
| B8 | 调研 C-1..C-29 + 规格 #274 + 工单 #276–#283 | 全互链 |
| B9 | 矩阵 ③ 组合 | PyRIT + PoisonedRAG + 自定义，偏离 0 |
| C4 | `python scripts/check_token_budget.py --check` | PASS |

术语决策：显式不增补 `GLOSSARY.md`（17491/17500，余量 9B + ADR-0006 共享长行 + 并行会话），
12 个新概念归一到既有条目，映射表见 `docs/operations/attack-rag-ch5-terms.md`。

## 5. code-review 双轴

- Standards：硬违规 1（Ch5 证据「确切命令」指向主链 CLI 的 rag-06..09，退出码 2）→ 已修（`runner._emit` 增可选 `command` 覆盖）+ 回归测试 `test_emitted_command_is_runnable`；复验 PASS。
- Spec：硬违规 0，判断项 5（AC15 降级记录仅落 SKILL.md 文字等）；无虚假覆盖声明；结论 PASS。
- 两轴最终 PASS，硬违规清零。

## 6. 差距关闭清单

| 项 | 状态 | 落点 | 文档依据 |
|---|---|---|---|
| P0-1 能力链 | 已实现 | `capability.py` / `readchain.py` / rag-06 | C-10..C-15 |
| P0-2 RoE/上传清单 | 已实现 | `SKILL.md` 前置 0 / rag-07 | C-7 |
| P0-3 规避技术 | 已实现 | `obfuscation.py` / rag-07 | C-17..C-21 |
| P1-4 信息提取/多主题碰撞 | 已实现 | `extract.py` / rag-08 | C-3/C-8/C-9 |
| P1-5 文档融合/隐蔽取证 | 已实现 | `blend.py` / rag-09 | C-22..C-24 |
| P2-6 架构基线/边界豁免 | 已实现 | `architecture.py` / `surface.py` / `SKILL.md` | C-1/C-2/C-15/C-16/C-29 |
| P2-7 慢滴投毒 | 已实现 | `slow_drip.py` / rag-09 | C-25..C-28 |

## 7. 收尾结论

- 提交：`feat/attack-rag` 分支主线提交 `8462805`（Ch5 增量）+ 验证文档 `ca7bc57`；推送通道：SSH 一次成功（两次推送均未用回退通道）；PR #308；CI S1–S4 见 PR checks。
- CI 收敛记录：首次 S1 因 PR 正文缺「契约变更清单」段 BLOCKED → 补齐后重跑因 C4 正文 3192/3000 字节 BLOCKED → 压缩正文至 2347 字节并本地复验契约门禁 PASS。
- `SKILL.md` 引用的工具/模块逐项核对：`capability.py`/`readchain.py`/`obfuscation.py`/`extract.py`/`blend.py`/`architecture.py`/`slow_drip.py`/`ch5.py`/`ch5_cli.py` 均存在。
- 未改共享长行；工作区无遗留未提交变更。
