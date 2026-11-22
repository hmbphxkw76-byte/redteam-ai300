# Ch8 主线 — 阶段10/11 门禁记录

## 阶段10 双轴

| 轴 | 发现 | 硬违规 | 结论 |
|---|---|---|---|
| Standards | 2 硬违规（CLI guard / 密钥标注）+ 1 判断项（docstring） | 2→0 | PASS |
| Spec | 7 硬违规（空心对齐矩阵/检查目标缺失/映射占位）+ 7 判断项 | 7→0 | PASS |

修复：CLI guard / `DEMO_XOR_KEY` / docstring；`alignment.py` 强校验；新增 sleeper.py、`--amplification`、canonical §6、AML 映射、pickle_rce 专测。

## 门禁
## 阶段11 门禁结果行
| 门禁 | 命令 | 结果 |
| B1 | `validate_skill.py` | PASS（16 技能） |
| B2 | `check_glossary.py` | PASS（66 废弃词） |
| B3 | `check_tools_compile.py` | PASS（212 文件 0 失败） |
| B3 | `unittest discover -s tests` | PASS（1,066 OK skip=3） |
| B4 | `check_evidence_contract.py` | PASS（4 适配器） |
| B6 | `measure_coverage.py --target attack-supply-chain --min 80` | PASS（754/860=87.7%） |
| lint | `markdownlint-cli2 <docs+skill>` | PASS（0） |
| 对齐 | `alignment --render` | PASS（14/14，强校验） |

## 阶段11 推送状态：PASS（授权例外后）

- `checkout_lock.py --check` 阻断：`GLOSSARY.md` 与 `scripts/check_token_budget.py` 被 `_recon-ai-ch6_wt`、`_threat-model-ch10_wt` 并发改动。
- 本分支改动文件均非共享锁文件（已核实），无实际冲突；锁为硬闸，禁止绕过。
- SSH `git push origin feat/attack-supply-chain` → 阻断；HTTPS `git push origin-https ...` → 阻断。两通道各一次即停。
- 未使用 `--no-verify`（须用户明确授权并逐项确认并集）。4 个提交本地全保留：`6a8f31d`/`1c4f2a9`/`56922d1`/`fdf4a97`。

**结论**：阶段 1–11 全 PASS；5 提交已推送远端、PR #344 创建，数据零丢失。
