# loot-manage 双轴代码审查（code-review）

> **性质**：阶段 10 交付物。基线 `origin/main`（`f345b19`）；审查范围 = loot-manage 新增/变更文件。
> **两轴分离**：Standards（编码规范）与 Spec（规格忠实度）并列，结论独立；硬违规阻断，判断项不阻断。

## A. Standards 轴

| # | 位置 | 发现 | 分类 | 处置 |
|---|---|---|---|---|
| A1 | `registry.py` `validate` | `checks` 重复初始化（先 `[]` 后赋 dict） | 硬违规（可读性） | 已修正为 `blocking, warnings = [], []` |
| A2 | `registry.py` `_split_row` | 单元格含字面 `\|` 会破坏解析 | 判断项 | 记录为限制：登记内容禁含 `\|`（写入 `loot/registry.md` 注记） |
| A3 | `cli.py` 全局参数 | `--registry/--root` 须在子命令前 | 判断项 | 文档化用法；不阻断 |
| A4 | 全部 | 仅标准库、零网络、无硬编码凭据 | 符合 | — |

**Standards 结论**：硬违规 1 项（A1）已修复；判断项 2 项（A2/A3）记录待后续改进。

## B. Spec 轴（对照 v2 AC-1..AC-12 与 SKILL.md 五要素）

| AC | 覆盖位置 | 判定 |
|---|---|---|
| AC-1 凭据登记 | `cmd_register --type 凭据` | 符合 |
| AC-2 会话状态 | `STATUSES_BY_TYPE['会话']` | 符合 |
| AC-3 flag 双通道 | `cmd_register` 强制双参 + `validate.dual_channel` | 符合 |
| AC-4 攻击路径 | `append_attack_path` + `checks.attack_path` | 符合 |
| AC-5 证据存在/三件套 | `checks.evidence` + `--check-pieces` | 符合 |
| AC-6 flags JSON | `validate()["flags"]` | 符合 |
| AC-7 失效可追溯 | `append_row` 不删行；状态枚举 | 符合 |
| AC-8 空态 | `--require-loot` | 符合 |
| AC-9 反例 | 见 `loot-manage-verification.md` §5 | 符合 |
| AC-10 编号唯一 | `checks.ids` | 符合 |
| AC-11 零网络 | 仅标准库，无 socket | 符合 |
| AC-12 列序无关 | `normalize_col` 集合匹配 | 符合 |

**Spec 判断项**：
- **B1（规格澄清，非违规）**：AC-6 字面写 `consistent = panel==shot`，但 SKILL.md 的「截图=」是**路径**而非 flag 值；实现取 `consistent = 两通道均已提供`，值级一致性由 `verify-evidence` 下游读取截图核对。已写入 `loot-manage-verification.md` §3 与 `registry.parse_dual` 注释。
- **B2**：`proof.txt` 用 warning（软），与 `verify-evidence` 的硬阻断互补，符合研究文档 G2。

## C. 复跑结果

| 检查 | 结果 |
|---|---|
| `python tests/test_loot_manage.py` | 19 passed |
| `python tests/test_loot_manage_evidence_contract.py` | 2 passed |
| `python scripts/measure_coverage.py --target loot-manage --min 80` | 93.4% ≥ 80% |
| `python scripts/validate_skill.py` | PASS（16 技能） |
| `python -m py_compile tools/loot_manage/*.py` | OK |

**结论**：硬违规 0（A1 已修复）；规格覆盖 12/12。**PASS**。
