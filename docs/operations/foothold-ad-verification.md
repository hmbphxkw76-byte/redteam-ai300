# foothold-ad 验证报告

> 对齐对象：`docs/operations/foothold-ad-design.md`（方案与实施清单 I-1..I-12、步骤设计 §3、边界 §2、选型 §4、风险 §6、范围 §8、主线声明 §9）。
> 判定口径：`PASS` = 命令实测通过且产出与方案一致；`PARTIAL` = 已实施但存在方案声明内的未完成部分；`未实施` = 方案明确排除或未启动。
> 本报告不对未完成项打勾（C8）。

## 1. 结论摘要

| 维度 | 数量 | 判定 |
|---|---|---|
| 实施清单 I-1..I-12 | 12 | 11 项 `PASS`，1 项 `PARTIAL`（I-12 见 §3.12） |
| 步骤设计 ad-01..ad-08 | 8 | 8 项已实现，判据与证据模板齐备 |
| 方案声明排除项 | 2 | `recon-ai` 影子端点（§8）、11 阶段主线（§9）均按声明未实施 |
| 门禁命令 | 13 | 13 项全绿（9 项主门禁 + 4 项补充门禁） |

**总体判定**：方案范围内可执行部分全部落地并通过门禁；`foothold-ad` 状态为**可执行增量**，主线阶段 1–11 待补，`capstone-rehearse` 中只记 `PARTIAL`。

## 2. 验证环境

- 平台：Windows（Git Bash），Python 3.13，仓库根 `D:/文档/GitHub/redteam-ai300`。
- 命令均为本机实测，输出摘要见 §3；未使用网络、未连接真实域环境（离线工件模式）。
- 工件夹具：`tests/foothold_ad/` 内以临时目录生成 `directory.json` / `templates.json` / `trusts.json` / `tickets.json` / `proof.json`。

## 3. 实施清单逐项对齐

| ID | 方案要求 | 实测命令 | 实测结果 | 判定 |
|---|---|---|---|---|
| I-1 | 新增 `skills/foothold-ad/SKILL.md` | `python scripts/validate_skill.py` | `PASS：共校验 20 个技能，全部合规`（含新增技能，9754 字节 / 上限 14000） | PASS |
| I-2 | 新增 `tools/foothold_ad/` 八个模块 | `python scripts/check_tools_compile.py` | `编译检查：282 个文件，失败 0`（清单已登记 `tools/foothold_ad`） | PASS |
| I-3 | 新增 `tests/foothold_ad/`，≥6 模块 | `python -m unittest discover -s tests/foothold_ad -t .` | `Ran 65 tests ... OK`（7 个测试模块 + 包初始化） | PASS |
| I-4 | 新包覆盖率 ≥90% | `python scripts/measure_coverage.py --target foothold-ad --min 90` | `总计 636/650 = 97.8%（门槛 90.0%）`，退出码 0 | PASS |
| I-5 | `GLOSSARY.md` 新增 AD 术语 | `python scripts/check_glossary.py` | `PASS：术语一致性校验通过（检查 66 个废弃术语）`；新增 4 条，见 §4.3 | PASS |
| I-6 | `consumers.md` 新增 `foothold-ad` 行（状态 `未合入`） | `python scripts/check_contract_consumers.py --check` | `契约消费者断言：PASS（全部消费者依赖均在契约清单中）` | PASS |
| I-7 | `tools_manifest.json` 登记编译包与覆盖率目标 | `python scripts/check_tools_compile.py --check-missing` | 新增文件不在「未登记」列表；覆盖率目标 `foothold-ad` 可被 `--target` 选中 | PASS |
| I-8 | `GOVERNANCE.md` §4.4 登记 | `python scripts/validate_skill.py` | 不再出现「未登记于 §4.4」告警 | PASS |
| I-9 | `capstone-rehearse` 流水线接入 | `python scripts/check_token_budget.py --check` | `结论：PASS`；流水线串已含 `foothold-ad` 并标注 `PARTIAL` | PASS |
| I-10 | 全量回归 | `python -m unittest discover -s tests -t . -q` | `Ran 1537 tests in 231.137s` / `OK (skipped=1)`，退出码 0 | PASS |
| I-11 | 预算与格式门禁 | `check_token_budget.py --check`；`npx markdownlint-cli2` | 预算 `PASS`（17 项锚点，缺失 0）；markdownlint 5 文件 `0 issues` | PASS |
| I-12 | 技能引用校验 | `python scripts/verify_skill_refs.py` | `PASS: SKILL.md Ch9 段全部引用字面完整` | PARTIAL（该脚本只校验 Ch9 段引用，不覆盖 `foothold-ad` 的路径引用；见 §5.2） |

### 3.10 全量回归结果

`python -m unittest discover -s tests -t . -q`：`Ran 1537 tests in 231.137s`，`OK (skipped=1)`，退出码 0。新增 65 例全部包含在内，既有 1472 例无回归。

### 3.13 补充门禁（CI S1 其余步骤）

| 门禁 | 命令 | 实测结果 | 判定 |
|---|---|---|---|
| 契约清单完整性 | `check_contract_manifest.py --check` | `契约清单校验：PASS。` | PASS |
| EvidenceWriter 契约 | `check_evidence_contract.py` | `PASS（4 个适配器：继承 + 最小签名 + 返回形态）` | PASS |
| PyRIT 版本漂移 | `python -m tools.pyrit_compat.checker check --root . --target 1.2.1` | `verdict: PASS`（warn=3，error=0） | PASS |
| 主线留痕发现 | `validate_skill_mainline.py --root .` | `foothold-ad GAP: 缺 docs/specs 规格 v1/v2；阶段门禁 0/10`；脚本退出码 0（只报告） | PASS（门禁不阻断；GAP 即方案 §9 声明项） |

## 4. 方案章节对齐

### 4.1 技能边界（方案 §2）

| 方案条款 | 实现落点 | 判定 |
|---|---|---|
| AD 特有面归 `foothold-ad` | `tools/foothold_ad/analyze.py` 六类判据，无入口/横向/提权逻辑 | PASS |
| 不改 `foothold-traditional` 判据 | 该技能文件零 diff | PASS |
| 复用 trad-08 移交清单 | SKILL.md「前置：接收立足点」三项前置 + 缺项 `BLOCKED` | PASS |
| 凭据即时登记 | SKILL.md 质量门第 7 条 | PASS（行为约束，非代码强制） |

### 4.2 步骤设计（方案 §3）

| 步骤 | 实现 | 判据测试 | 判定 |
|---|---|---|---|
| ad-01 | `assess()` 信任分支 | `test_full_chain`、`test_empty_and_partial_inputs`、`test_domain_missing_without_trusts_is_undetermined` | PASS |
| ad-02 | `kerberoastable` / `asrep_roastable` / `unconstrained` | `KerberosTest` 全组、`test_unknown_fields_propagate_undetermined` | PASS |
| ad-03 | `assess(tickets=...)` | `test_full_chain`、`test_empty_and_partial_inputs` | PASS |
| ad-04 | `adcs_risks`（ESC1/ESC8） | `AdcsTest` 全组、`test_esc8_only_is_exposed`、`test_strong_templates_are_absent` | PASS |
| ad-05 | `dcsync_principals` | `DcsyncTest`、`test_partial_dcsync_is_exposed` | PASS |
| ad-06 | `trust_risks` + `path_to_domain_admin` | `TrustTest`、`PathTest`、`test_trust_risk_without_cross_domain_is_exposed` | PASS |
| ad-07 | `assess(proof=...)` 双通道比对 | `test_full_chain`、`test_proof_mismatch_blocks` | PASS |
| ad-08 | `assess()` 汇总分支 | `test_full_chain`、`test_empty_and_partial_inputs` | PASS |

### 4.3 技术选型（方案 §4）

| 条款 | 实测依据 | 判定 |
|---|---|---|
| 零第三方依赖 | `tools/foothold_ad/*` 仅 `json`/`os`/`re`/`argparse` 等标准库 | PASS |
| 零 PyRIT | 无 `pyrit` 引用 | PASS |
| 离线优先 | 全部判据以文件为输入；缺件 `BLOCKED`（`test_missing_artifacts_block_dependent_steps`） | PASS |
| 凭据不落盘 | `fingerprint_hash` 只返回前 8 位 + 长度；`test_no_plaintext.py` 三项断言 | PASS |
| 术语新增 | 域信任 / 票据攻击 / 目录复制 / 模板利用 4 条，均带 `foothold-ad` 步骤号 | PASS |

### 4.4 风险与失败模式（方案 §6）

| 风险 | 实现 | 测试 | 判定 |
|---|---|---|---|
| 无工件 | `runner.REQUIRED_ARTIFACTS` → `BLOCKED` + 缺失文件名 | `test_missing_artifacts_block_dependent_steps` | PASS |
| 字段缺失 | `None` 保留 → `UNDETERMINED` + 依据 | `test_unknown_fields_propagate_undetermined` | PASS |
| 明文凭据外泄 | 解析不保留 hash 字段、指纹化 | `NoPlaintextTest` 三项 | PASS |
| 跨域越权 | SKILL.md 前置第 2 条（ACL 决策表复核） | 行为约束，无代码断言 | PARTIAL（见 §5.3） |
| 语境混淆 | SKILL.md 语境门（`course-capstone` / `osai-rehearsal`） | 行为约束 | PARTIAL（见 §5.3） |

## 5. 偏差与未完成项

### 5.1 术语表：改为上调预算而非压缩腾位（方案 I-5 的措辞偏差）

实测 `GLOSSARY.md` 归一化后为 **21500/21500，余量 0**；最长既有条目仅 349 字节，压缩 3–5 条收益不足 200 字节，无法容纳 783 字节的术语块。处置：按 ADR-0005「基线 + 必要增量」与 ADR-0006「并集后 + 余量」将上限 21500 → 23000（实测 22283，留 ~717B），未删除任何既有术语。偏差已在 `scripts/check_token_budget.py` 注释留痕。

### 5.2 I-12 判定为 PARTIAL 的理由

`scripts/verify_skill_refs.py` 的实际校验范围是 `SKILL.md` 中 Ch9 段的字面引用完整性，不覆盖 `foothold-ad` 的 `tools/foothold_ad/` 路径是否可达。本报告的替代验证为：`check_tools_compile` 编译全部模块 + `measure_coverage` 实际导入六个模块并跑通 65 例，间接证明路径可达。方案清单中的 I-12 表述（「技能引用校验」）与实际脚本能力不符，属方案侧精度不足，非实施缺口。

### 5.3 行为约束未代码化

「跨域动作须先核对 ACL 决策表」「语境门」两条仅写入 SKILL.md 与设计文档，无代码断言。理由：两者依赖运行时上下文（ACL 表、考试语境），离线工件模式无法表达；强行代码化会产生「假绿灯」。如需强制，应在 `verify-evidence` 增加报告侧检查，属后续增量。

### 5.4 方案明确排除、未实施

| 项 | 状态 | 依据 |
|---|---|---|
| `recon-ai` 影子端点（方案 §8） | 未实施 | 涉及冻结契约（`recon-01..07`、七字段），方案给出 A/B 两案与契约影响，留待主线 G0 择一 |
| 11 阶段主线（方案 §9） | 未执行 | to-spec 两遍与逐阶段 G0 记录未产出；`research` 仅完成课程文档一手源，外部权威源未逐条核实 |
| 真实域环境联调 | 未执行 | 无 AD 靶场；技能按设计以离线工件交付，实跑需 Ch11 三域环境 |

## 6. 复现命令

```bash
python -m unittest discover -s tests/foothold_ad -t .
python scripts/measure_coverage.py --target foothold-ad --min 90
python scripts/validate_skill.py
python scripts/check_glossary.py
python scripts/check_tools_compile.py
python scripts/check_contract_consumers.py --check
python scripts/check_token_budget.py --check
python scripts/verify_skill_refs.py
npx markdownlint-cli2 "docs/operations/foothold-ad-design.md" "skills/foothold-ad/SKILL.md"
```

## 7. 变更文件清单

| 类型 | 路径 |
|---|---|
| 新增 | `skills/foothold-ad/SKILL.md` |
| 新增 | `tools/foothold_ad/{__init__,__main__,model,artifact,analyze,evidence,runner,cli}.py` |
| 新增 | `tools/foothold_ad/{provenance,preflight}.py`（第二轮） |
| 新增 | `tests/foothold_ad/{__init__,test_model,test_artifact,test_analyze,test_evidence,test_runner,test_cli,test_no_plaintext}.py` |
| 新增 | `tests/foothold_ad/{test_hardening,test_provenance,test_preflight}.py`（第二轮） |
| 新增 | `docs/operations/foothold-ad-design.md`、`docs/operations/foothold-ad-verification.md` |
| 修改 | `GLOSSARY.md`（+4 条域渗透术语） |
| 修改 | `docs/contracts/consumers.md`（+1 行，状态 `未合入`） |
| 修改 | `scripts/tools_manifest.json`（+编译包、+覆盖率目标与模块清单） |
| 修改 | `scripts/measure_coverage.py`（+`ALL_TARGET_ORDER` 条目） |
| 修改 | `scripts/check_token_budget.py`（`GLOSSARY.md` 上限 21500 → 23000，含理由注释） |
| 修改 | `docs/governance/GOVERNANCE.md`（§4.4 +1 行） |
| 修改 | `skills/capstone-rehearse/SKILL.md`（流水线串接入 `foothold-ad`） |

## 8. 补遗：最佳实践对齐（第二轮，方案 §10–§11）

> 对齐目标：无真实 AD 环境下做到「可追溯、不臆断、可复现」。方案清单编号 I-13..I-18，见设计文档 §10；标准映射见 §11。

### 8.1 清单逐项对齐

| ID | 改进 | 实测命令 | 实测结果 | 判定 |
|---|---|---|---|---|
| I-13 | 工件来源与完整性 | `python -m unittest tests.foothold_ad.test_provenance`；`cli verify` | 完整清单退出码 0、篡改退出码 1（`test_verify_exit_zero_for_complete_artifacts` / `test_verify_exit_one_for_tampered_artifacts`）；无清单时全部文件列 `untrusted` | PASS |
| I-14 | schema 版本 | `test_hardening.SchemaTest` | `schema_version=2.0` → `ad-02` 记 `UNDETERMINED` 且注记含版本；1.0/1.1 正常；缺省兼容 | PASS |
| I-15 | 未知枚举不推断 | `test_hardening.UnknownEnumTest` | 未知信任方向、未知委派、缺授权签名、缺 EPA 一律 `UNDETERMINED`；EPA 已启用不算 ESC8 | PASS |
| I-16 | 畸形与对抗输入 | `test_hardening.CorruptArtifactTest` / `MalformedContentTest` | 空文件、截断、非 UTF-8 → `BLOCKED` + `parse_errors`；超深嵌套、超限体积 → `ArtifactError`；同形字不合并、循环 ACE 终止、类型错乱不推断 | PASS |
| I-17 | 确定性与快照 | `test_hardening.DeterminismTest` | 同输入两次 `digest` 相同；JSON 键序反转后 `digest` 不变；输入变化 → `digest` 变化 | PASS |
| I-18 | 采集前置清单 | `cli preflight`；`test_preflight` | 五类工件缺失/已存在分层输出；每条含采集命令、期望字段、依赖步骤；`artifact_manifest.json` 缺失显式提示 | PASS |

### 8.2 判据收紧（对齐官方定义）

| 判据 | 收紧前 | 收紧后 | 依据 |
|---|---|---|---|
| ESC1 | 可控主体 + 客户端认证 EKU + 低权注册 + 无审批 | 追加「无授权签名」，审批/授权签名字段缺失即 `UNDETERMINED` | SpecterOps Certified Pre-Owned（ESC1 = No Issuance Requirements + …） |
| ESC8 | HTTP 注册端点存在 | 追加「EPA 未启用」，EPA 未知记 `UNDETERMINED`，EPA 启用不命中 | 同上（ESC8 = NTLM Relay to AD CS HTTP Endpoints） |

### 8.3 回归与门禁（第二轮实测）

| 门禁 | 结果 |
|---|---|
| 本包测试 | `Ran 102 tests ... OK`（第一轮 65 + 新增 37） |
| 本包覆盖率 | `941/956 = 98.4%`，最低模块 93.3%（门槛 90%） |
| 全量回归 | 见 §8.4 复跑结果 |
| 其他门禁 | 见 §8.4 复跑结果 |

### 8.4 复跑记录

| 门禁 | 命令 | 实测结果 | 判定 |
|---|---|---|---|
| 本包测试 | `python -m unittest discover -s tests/foothold_ad -t .` | `Ran 102 tests in 0.430s` / `OK` | PASS |
| 本包覆盖率 | `measure_coverage.py --target foothold-ad --min 90` | `941/956 = 98.4%`（artifact 98.7 / analyze 99.1 / runner 99.3 / provenance 99.1 / preflight 98.8 / cli 93.3） | PASS |
| 全量回归 | `python -m unittest discover -s tests -t . -q` | `Ran 1574 tests in 192.716s` / `OK (skipped=1)`，退出码 0 | PASS |
| 端到端 verify | `cli verify`（清单完整 / 追加一字节后） | 完整退出码 0；篡改退出码 1 且 `untrusted` 含 `directory.json` | PASS |
| 端到端 preflight | `cli preflight --artifacts <DIR>` | 退出码 0，输出 31 行，含「采集:」与字段清单 | PASS |
| 端到端 analyze | `cli analyze --steps ad-02` | 退出码 0，输出含 `digest`，`provenance.ok=false`（因工件已被改动） | PASS |
| 技能合规 | `validate_skill.py` | `PASS：共校验 20 个技能，全部合规。` | PASS |
| 术语一致性 | `check_glossary.py` | `PASS（66 个废弃术语）` | PASS |
| 编译门禁 | `check_tools_compile.py` | `编译检查：284 个文件，失败 0` | PASS |
| 契约消费者 | `check_contract_consumers.py --check` | `PASS（全部消费者依赖均在契约清单中）` | PASS |
| 契约清单 | `check_contract_manifest.py --check` | `契约清单校验：PASS。` | PASS |
| EvidenceWriter | `check_evidence_contract.py` | `PASS（4 个适配器）` | PASS |
| 技能引用 | `verify_skill_refs.py` | `PASS: SKILL.md Ch9 段全部引用字面完整` | PASS |
| Token 预算 | `check_token_budget.py --check` | `结论：PASS（产物预算 + 规范契约均齐全）` | PASS |
| 格式 | `markdownlint-cli2`（3 个改动 md） | `0 issues` | PASS |

文档体积：设计 12238B / 验证 14080B（上限均 17000）；`SKILL.md` 11830B（上限 14000）。

### 8.5 未改变项

- ad-01..ad-08 的判据语义除 ESC1/ESC8 收紧外未改动；`foothold-traditional`、`report-exam`、证据片段契约零改动。
- 主线 11 阶段仍未执行（设计文档 §9）；`validate_skill_mainline.py` 对 `foothold-ad` 仍报 `GAP`，属预期。
- `recon-ai` 影子端点仍未实施（设计文档 §8）。
