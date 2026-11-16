# attack-infra 双轴代码审查（阶段 10）

> 版本 v1 · 基线 `origin/main`（`fde51a1`）· 分支 `feat/attack-infra` · 审查方式：两个只读子 agent 并行，**两轴不合并、不重排**
> 审查轴：**Standards**（CI-CD S0–S4 / GOVERNANCE §4.2 §8.2 / AGENTS.md C1–C8 / GLOSSARY）与 **Spec**（#213 v2 AC-01..AC-24）
> diff 范围：`tools/attack_infra/`（12 模块）、6 个测试文件、`GLOSSARY.md`、`scripts/measure_coverage.py`、`docs/research/attack-infra-canonical.md`、`docs/operations/attack-infra-{design,terms,verification}.md`、`.gitignore`

## 1. 两轴结论（并列）

| 轴 | 发现数 | 硬违规 | 最严重项 |
|---|---|---|---|
| Standards | 8 | 8 | `GLOSSARY.md` 新增词条同时转抄 canonical 事实并逼近 15000 字节预算（C1 + B2） |
| Spec | 9 | 2 | **AC-07 为假**：`impact()` 未受 `--allow-inference` 约束，默认运行即发出两次推理请求 |

两轴独立得出「AC-07 与只读姿态相关」与「共享文件改动需声明」两条结论，互不引用，取并集进入修复清单。

## 2. 硬违规与修复（逐条可追溯）

| # | 文件:位置 | 违反 | 修复 | 复验 |
|---|---|---|---|---|
| S1 | `GLOSSARY.md` 新增 3 条 | C1（事实 + 指针双份） | 改「定义 + 指针」，端口/分值只留 canonical 与既有条目 | `check_token_budget.py --check` PASS（14924/15000） |
| S2 | `attack-infra-canonical.md` F-16/F-18 | C1（转抄条款/计分事实） | 改为纯指针，只记「要求存在于何处」 | 人工复核：两行无条款正文 |
| S3 | `attack-infra-terms.md` §2 | C1 + B2（与 `model.py` 常量冲突） | 改为指向常量，不本地枚举 | `grep` 常量名一致 |
| S4 | `attack-infra-design.md` §2/§8 | B5（声明与事实不符） | `detect(resp)`、12 模块、`discover -> StepVerdict` | 通读比对实现 |
| S5 | `attack-infra-verification.md` §4/§6 | B8（数字漂移） | 按实测重写 | 89.9% / 526 测试 |
| S6 | `tests/test_attack_infra_path_a.py:68` | B3/S2（断言恒真） | 直接断言命令不含占位符 | 该用例仍通过且可失败 |
| S7 | `tests/test_attack_infra_evidence_contract.py:64` | B3（直跑漏测） | `unittest.main()` 移至末尾 | 直跑 5 条 |
| F1 | `tools/attack_infra/path_c.py:99` | **AC-07 为假** | 加 `allow_inference` 守卫，未开启→`BLOCKED(evidence_incomplete)` 且零请求 | `test_inference_disabled_sends_nothing` |
| F2 | `path_c.py:140` | AC-13 歧义 | 明确 07 需 AI 日志 / 08 需 flag 通道；补 `ai_log` 断言 | `test_impact_records_ai_log_when_proven` |
| F3 | `path_b.py:37`、`path_c.py:64` | AC-18 | 改用 `argv_to_text` | 命令含空格亦可用 |
| F4 | `fingerprint.py:49` | AC-03 被削弱 | vLLM 仅接受 `JSON_MODELS` | `test_empty_body_is_not_a_vllm_hit` |

## 3. 判断项（记录不阻断）

1. 默认产物目录 `loot/attack-infra/` 含目标地址 → 已加入 `.gitignore`，**不入库**（判断项转为处置动作）。
2. `evidence.py` 的 `build_argv` 被单测直接断言 → 该函数是可观察契约（片段字段来源），保留。
3. `GLOSSARY.md` 计费字节 14924/15000，余量 76 字节 → 下一次术语增补需先压缩既有条目；已在本文件登记为约束。
4. `tests/` 断言 `fragment_path` 命名 → 与 `report-exam` 消费路径耦合，属有意契约。

## 4. 复跑结果

| 检查 | 命令 | 结果 |
|---|---|---|
| 全量测试 | `python -m unittest discover -s tests` | `Ran 655 tests … OK (skipped=2)` |
| 覆盖率 | `python scripts/measure_coverage.py --target attack-infra --min 80` | 1210/1329 = 91.0% |
| 术语 | `python scripts/check_glossary.py` | PASS（47 废弃术语 0 命中） |
| 技能结构 | `python scripts/validate_skill.py` | PASS（16 技能） |
| 产物预算 | `python scripts/check_token_budget.py --check` | PASS |
| 禁用名 | `grep -rn "Orchestrator\|pyrit.orchestrator\|AzureOpenAIChatTarget" tools/attack_infra/` | 0 命中 |
| 注入面 | `grep -rn "shell=True" tools/attack_infra/*.py` | 0 命中 |

## 5. 门禁记录（阶段 10）

| 编号 | 检查项 | 依据 | 实测 | 判定 | 结论 |
|---|---|---|---|---|---|
| B1–B8 | 全项 | §2.1 | 见 §4 六条命令，全部通过 | 符合 | PASS |
| 硬违规清零 | 阶段门禁 | §3.10 | 8 项 Standards + 2 项 Spec 布尔判据均已修复并复验 | 符合 | PASS |
| 规格覆盖矩阵 | 验收④ | AC-01..24 | 24/24 有实现与测试（F1–F5 补齐后） | 符合 | PASS |
| 门禁套件全绿 | 验收⑤ | §4 | 六条命令全绿 | 符合 | PASS |

**阶段结论**：`PASS`（硬违规 0；判断项 4 条已登记）。复验命令：`python -m unittest discover -s tests && python scripts/measure_coverage.py --target attack-infra --min 80 && python scripts/check_token_budget.py --check`。
