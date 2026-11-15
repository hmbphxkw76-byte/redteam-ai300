# attack-embeddings 双轴代码审查（阶段 10）

> 基线：`origin/main`（f345b19）→ `feat/attack-embeddings`。两轴并列，不合并。
> 硬违规：阻断交付；判断项：记录为改进项，不阻断。

## 轴 A — Standards（编码规范 / 工程标准）

| # | 检查 | 结论 | 分类 |
|---|---|---|---|
| A1 | `py_compile` 全部模块 | 通过 | — |
| A2 | 零第三方依赖；无 `pyrit.orchestrator`/`*Orchestrator`/`XpiaAttack`/`AzureOpenAIChatTarget`（B7） | grep 无命中 | — |
| A3 | 无硬编码凭据（B5） | grep 无 `sk-`/api-key | — |
| A4 | 判定级别取自四值集合 `LEVELS`（`StepVerdict.__post_init__` 校验） | 通过 | — |
| A5 | 叶节点模块只含数据/纯计算；IO 集中在 runner/evidence | 符合 | — |
| A6 | 命名与术语符合 `GLOSSARY.md` | 符合 | — |
| A7 | `rag_impact` 函数内局部导入 harness 规避环依赖 | 可接受 | 判断项（改进：抽 `clone_with()`） |
| A8 | `cli.py` argparse 错误分支未单测 | 可接受 | 判断项（改进：补错误路径用例） |

硬违规数：**0**。

## 轴 B — Spec（规格忠实度 / 覆盖矩阵）

| AC | 实现位置 | 测试 | 状态 |
|---|---|---|---|
| AC-1 面枚举 | `runner.run_attack` emb-01 | `test_surface_enumeration` | 覆盖 |
| AC-2 维度探测 | emb-02 | `test_probe_dimensions` | 覆盖 |
| AC-3 反演 | `attacks.invert` | `test_invert_exact_match` | 覆盖 |
| AC-4 成员推断 | `attacks.membership_inference/auc` | `test_membership_auc`、`test_membership_single` | 覆盖 |
| AC-5 对抗样本 | `attacks.adversarial_shift` | `test_adversarial_shift` | 覆盖 |
| AC-6 向量库反查 | `attacks.vector_lookup` | `test_vector_lookup(_empty_store)` | 覆盖 |
| AC-7 下游影响 | `attacks.rag_impact` + emb-07 | `test_rag_impact` | 覆盖 |
| AC-8 flag 双通道 | emb-08 | `test_flag_dual_channel` | 覆盖 |
| AC-9 可复现 | 全链路 | `test_reproducible`、`test_cli_main` | 覆盖 |
| AC-10 证据契约 | `evidence` seam + `_emit` | `test_evidence_wiring` + SKILL 契约测试 | 覆盖 |
| AC-11 降级 | `run_attack(has_surface=False)` | `test_fallback_paths`、`test_cli_degraded` | 覆盖 |

- 覆盖率：**95.6%**（16 用例；cli 96.2%、runner 100%）。
- 判断项：emb-08 无真实 flag 时返回「部分生效 / 校验预言机等价」，与 AC-8 允许口径一致；非违规。

硬违规数：**0**。

## 结论

两轴硬违规均为 0；判断项 3 条（A7、A8、emb-08 口径）记录为后续改进，不阻断。门禁套件全绿。
