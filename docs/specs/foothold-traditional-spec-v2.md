# foothold-traditional — 工程规格 v2

> 回溯整理：依据 `skills/foothold-traditional/SKILL.md` 与既有实现、测试归纳；**不代表原流程按序执行**。
> 整理日期：2026-11-27　状态：定稿（v2）

## 1. v1 → v2 差异清单

| 差异 | v1 表述 | v2 收敛 | 理由 |
|---|---|---|---|
| 验收形态 | 使用者与触发场景、行为约束 | 16 条布尔 AC（AC-01..AC-16） | 可机器或人工判定 |
| 主链证据 | 「每步三件套」 | AC-01/AC-03 绑定文本契约测试 | 把质量门升级为机器强制 |
| Ch9 判据 | 「类型化五值结论」 | AC-04..AC-09 绑定三个测试模块 | 命中/缺项/拒绝成对覆盖 |
| 证据发射 | 「经 strict 落盘」 | AC-10..AC-13 断言参数与失败语义 | 出口唯一且可复制 |
| 编排 | 「两步编排」 | AC-14 断言步序、未知步、可选附着 | 未知步骤必须显式失败 |
| 人工项 | 双通道与前后权限证明 | AC-15 明确为人工判据 | 无运行时截图/面板接口 |
| 覆盖率 | 未声明 | AC-16 按实测判定 | 2026-11-27 补登记后首测 97.6% |

## 2. 布尔验收条件

| 编号 | 条件（可真/可假） | 复验方式 |
|---|---|---|
| AC-01 | `trad-01`..`trad-08` 各自恰有一次 `collect_evidence.py --step trad-0N` 调用 | `test_foothold_traditional_evidence_contract` 两例 |
| AC-02 | `SKILL.md` 不含契约测试 `AVOID_TERMS` 声明的两个废弃同义词 | 同上 `test_no_avoid_terms_in_skill` |
| AC-03 | 每个 Ch9 结论的命令、输出、截图钩子三字段均非空 | `test_foothold_traditional_ch9` `test_ac07_three_pieces` |
| AC-04 | outcome 枚举恰 5 个；未知 outcome 或非既有 reason 抛 `ValueError` | hardening `test_ac07_five_values_and_reasons` |
| AC-05 | 响应含三个 AWS 键名时判 `EXPOSED_NO_AUTH` 且指纹数为 3 | hardening `test_ac01_three_fingerprints` |
| AC-06 | 无键名判 `ABSENT`/`none_found`；响应含 `AccessDenied` 判 `AUTH_REQUIRED`/`forbidden` | hardening `test_ac02_none_found`、`test_ac02_forbidden` |
| AC-07 | 明文凭据不出现在 output 与指纹文本；裸值、双引号、单引号三种写法均脱敏 | hardening `test_ac03_no_plaintext`、`test_ac03_quoted_values_no_bypass` |
| AC-08 | 身份验证返回 `Arn` 才判 `EXPLOITED`；验证失败仍判 `EXPOSED_NO_AUTH` | hardening `test_ac04_verified_exploited`、`test_ac04_verify_no_arn_not_exploited` |
| AC-09 | `sudo -l` 含 `(root) NOPASSWD:` 时 `wrappers` 收录脚本；无该项判 `ABSENT`；无 sudo 判 `no_tool` | hardening `test_ac05_wrappers`、`test_ac06_no_nopasswd`、`test_ac06_no_tool` |
| AC-10 | strict 参数含 `--step`/`--cmd`/`--output`/`--shot-cmd`/`--out`/`--strict`/`--target`，且工具路径为 `tools/collect_evidence.py` | hardening `test_ac08_build_argv_strict` |
| AC-11 | strict 成功时 `evidence_ok=True`、`exit_code=0`、路径为 `<out_dir>/<step_id>.md`；失败时 `False` 且含 `evidence_error` | hardening `test_ac08_strict_ok`、`test_ac08_strict_fail` |
| AC-12 | 存在指纹时参数额外含 `--note fingerprint:<键名(len=N)@位置>` | hardening `test_ac08_note_fingerprints` |
| AC-13 | 证据模块源码不含 `shell=True` | hardening `test_ac09_no_shell_true` |
| AC-14 | 两步执行均附着证据；未知 step 抛 `ValueError`；`attach=None` 不写证据路径 | hardening 三个 runner 用例 |
| AC-15 | 主链 flag 双通道一致、提权前后 `id` 同屏、横向路径图与移交清单齐备 | 人工判据：`SKILL.md` 质量门逐项核对，无自动断言 |
| AC-16 | 覆盖率按 `--target` 口径可复现 | 可判定：2026-11-27 已登记目标，`--target foothold-traditional` → 165/169 = 97.6%（32 例全过） |

## 3. 测试决策

- 分层：模型层（`ch9_model`）、判据层（`ch9_entry`）、证据层（`ch9_evidence`）、编排层（`ch9_runner`），四层各有独立测试类。
- 离线夹具：命令执行以 `FakeCommand` 注入，不触网、不启进程、不依赖第三方。
- 只断言外部行为：给定上下文得到 outcome/reason/指纹/命令/输出与 CLI 参数，不断言私有辅助函数。
- 成对反例：SSRF 命中/无键名/被拒；GPU 有包装脚本/无 NOPASSWD/无 sudo；证据成功/失败。
- 主链 `trad-01`..`trad-08` 是文档契约而非运行时代码，以 `SKILL.md` 文本断言覆盖；不得据此宣称运行时已验证。
- 确定性：同输入同结论，指纹为不可变元组；类型校验在构造期失败。
- 覆盖率：2026-11-27 补登记目标后首测 97.6%（165/169，见 AC-16）。

## 4. 门禁映射

| 门禁 | 命令 | 与 AC 的关系 |
|---|---|---|
| 单元测试 | `python -m unittest discover -s tests/foothold_traditional -t . -q` | AC-01..AC-14 |
| 覆盖率 | `measure_coverage.py --target foothold-traditional` | AC-16；165/169 = 97.6%，命令可执行 |
| 引用完整性 | `python scripts/verify_skill_refs.py` | Ch9 段 `SKILL.md` 引用字面完整 |
| 编译 | `python -m py_compile tools/foothold_traditional/*.py` | 包可导入 |
| 技能合规 | `python scripts/validate_skill.py` | 四要素与 front-matter |
| 术语 | `python scripts/check_glossary.py` | AC-02 的仓库级扩展 |
| 预算 | `python scripts/check_token_budget.py --check` | 文档体积上限 |

## 5. 证据与可观测性

- 唯一证据出口为仓库共享工具 `tools/collect_evidence.py`；本技能只组装参数列表，不自建证据实现。
- 每个结论对象带 `evidence_ok`、`exit_code`、`argv`、`evidence_error` 四个可观测字段，失败不抛异常。
- 凭据仅以 `Fingerprint`（键名 + 长度 + 位置）形式进入参数与证据，明文经脱敏后才进入 output。
- 证据路径约定为 `<out_dir>/<step_id>.md`；主链产物落 `loot/trad-0N-*.md`，移交清单落 `loot/handoff.md`。
- 可观测面即结论字段本身，无需额外日志；不落明文、不落 shell 拼接。

## 6. 风险与待验证

| 风险 | 影响 | 待验证或闸门 |
|---|---|---|
| 无真实演练环境，判据仅夹具验证 | 规则可能在真实目标漏判或误判 | 表述限定「夹具验证」；实跑前须复核 |
| 主链八步无运行时代码，仅文本契约 | 文档漂移导致证据步骤缺失 | AC-01/AC-03 测试拦截 |
| `coverage_targets` 未登记该技能 | 覆盖率质量门无法按项目口径判定 | 建议后续在 `scripts/tools_manifest.json` 补登记 |
| SSRF 正则覆盖裸值与引号值，未覆盖转义序列或编码载荷 | 漏识别凭据键名 | 待补负向夹具后再扩展 |
| 五值 reason 集合依赖 `tools/attack_infra` 既有枚举 | 上游变更引发构造期异常 | 上游改动须同步复跑本套测试 |
| 规格晚于实现（回溯整理） | 存在「按实现写规格」的循环论证风险 | 差异清单与门禁记录如实标注，不改写结论 |
