# Ch8 主线 — 阶段10/11 门禁记录

> **分支** `feat/attack-supply-chain` · **基线** `origin/main`@c63edeb · **commits** `6a8f31d`（实现）+ `1c4f2a9`（PR）+ 修复提交

## 阶段10 双轴

| 轴 | 发现 | 硬违规 | 结论 |
|---|---|---|---|
| Standards | 2 硬违规（CLI guard / 密钥标注）+ 1 判断项（docstring） | 2→0 | PASS |
| Spec | 7 硬违规（空心对齐矩阵/检查目标缺失/映射占位）+ 7 判断项 | 7→0 | PASS |

修复：CLI guard / `DEMO_XOR_KEY` / docstring；`alignment.py` AST+用例+证据强校验；新增 sleeper.py、`--amplification`、canonical §6、AML 映射、pickle_rce 专测。

## 阶段11 门禁结果行

| 门禁 | 命令 | 结果 |
|---|---|---|
| B1 | `validate_skill.py` | PASS（16 技能） |
| B2 | `check_glossary.py` | PASS（66 废弃词） |
| B3 | `check_tools_compile.py` | PASS（211 文件 0 失败） |
| B3 | `unittest discover -s tests` | PASS（1,062 OK skip=3） |
| B4 | `check_evidence_contract.py` | PASS（4 适配器） |
| B6 | `measure_coverage.py --target attack-supply-chain --min 80` | PASS（728/825=88.2%） |
| C4 | `check_token_budget.py --check` | PASS |
| lint | `markdownlint-cli2 <docs+skill>` | PASS（0） |
| 对齐 | `alignment --render` | PASS（14/14，强校验） |
| 证据 | `alignment --generate-evidence` | PASS（9/9 rc=0） |

## 对齐矩阵

`alignment --render` → 14 行全 PASS；四元组（锚点/实现+AST标识/测试/证据配方）定义见 `alignment.py#ROWS/#EVIDENCE_RECIPES`。

## C4 产物

spec-v1 5,363/8,000 · v2 7,221/10,000 · PR 2,9xx/3,000 · canonical 14,xxx/16,000 · design 4,438/17,000 · SKILL 10,841/12,000。

## 推送与结论

检出锁 `checkout_lock.py --check` 推送前实测；SSH → HTTPS 各一次即停。PR 含「契约变更清单」段，互链 #336/#337–343。
**结论**：硬违规清零、14/14 强校验对齐、门禁全绿、覆盖率 88.2%；检出锁阻断则停留阶段 11（ADR-0006）。
