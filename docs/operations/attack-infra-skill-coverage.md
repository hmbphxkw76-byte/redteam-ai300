# attack-infra SKILL.md 逐条核对与推送留痕

> 版本 v1.0 · 输入 `skills/attack-infra/SKILL.md`、规格 #213 v2、`docs/operations/attack-infra-verification.md`
> 性质：阶段 8/11 完整性证据。核对结论：声明项 39 条，全部有实现位置与验证方式，遗漏 0。

## 1. SKILL.md 逐条核对（实现完整性）

> 核对对象：`skills/attack-infra/SKILL.md` 全部声明项（front-matter、执行体 8 步、质量门 7 条、校验标准 3 条、失败与豁免 4 条）。

| SKILL.md 条目 | 实现位置 | 验证方式 | 状态 |
|---|---|---|---|
| front-matter `output`：每步命令+输出+截图 | `runner.attach_evidence` → `evidence.EvidenceWriter` | 8 份片段三件套齐备（§2） | 已实现 |
| front-matter `output`：利用前后对照 | `report._before_after`（基线 vs `EXPLOITED` 步骤） | 报告「利用前后对照」小节；`BeforeAfterReportTests` | 已实现 |
| front-matter `output`：下游模型服务器/推理滥用取证 | `path_c.impact`（before/after + AI 日志） | `ImpactTests` 5 例 | 已实现 |
| front-matter `output`：`ai_vector.txt` flag 取证 | `path_c.flag`（双通道一致性） | `FlagTests` 3 例 | 已实现 |
| 前置 1：复用 recon-ai 资产清单 | `inventory.load_endpoints` + `path_a._probe_pairs` + `--inventory` | `InventoryTests` 3 例、`InventoryDiscoverTests` | 已实现 |
| 前置 2：记录正常部署基线（端口/鉴权/服务账号） | `path_a.discover` 输出（端口、状态码、鉴权态）+ 报告基线表 | 实测输出 7 端点；`discover` 测试 5 例 | 已实现 |
| 攻击路径 A · infra-01 发现面 | `path_a.discover` | 活体 3 命中 / 4 未命中 | 已实现 |
| 攻击路径 A · infra-02 云平台配置错误 | `path_a.cloud_misconfig`（`--no-sign-request`） | `CloudTests` 4 例 | 已实现 |
| 攻击路径 A · infra-03 模型服务器暴露/滥用 | `path_a.model_server`（列举 + 单次推理） | 活体 `EXPLOITED`；`ModelServerTests` 4 例 | 已实现 |
| 攻击路径 B · infra-04 容器化负载越权 | `path_b.container`（`auth can-i --list`、`--as=`） | `ContainerTests` 5 例 | 已实现 |
| 攻击路径 B · infra-05 推理网关凭据泄露 | `path_b.gateway`（仅指纹） | `GatewayTests` 5 例 | 已实现 |
| 攻击路径 C · infra-06 提权 → 代码执行 | `path_c.privesc`（回显归属校验） | `PrivescTests` 5 例 | 已实现 |
| 攻击路径 C · infra-07 下游影响取证 | `path_c.impact`（稳定化对照 + AI 日志） | 活体判 `no_difference`；`ImpactTests` 5 例 | 已实现 |
| 攻击路径 C · infra-08 flag 取证（AI向量机 / 独立机） | `path_c.flag` + `runner.run_targets`（`--secondary-target`） | `TargetScopeTests` 4 例 | 已实现 |
| 步骤 9：访问证明 `whoami`/`id` + flag 同屏 | `path_c.flag` 命令串含 `whoami; id`；flag 双通道断言 | `FlagTests` | 已实现 |
| 质量门 1：每步可 copy/paste 命令 | `command.curl_json` / `argv_to_text`；报告复现段 | AC-18 断言 + 人工复跑 | 已实现 |
| 质量门 2：关键输出原文 | 每步 `output` 字段 | 8 份片段 | 已实现 |
| 质量门 3：截图（访问证明） | `shot.ShotPlanner`（只产计划，钩子入片段） | 片段「截图捕获钩子」行 | 已实现 |
| 质量门 4：利用前后对照 | 见上（报告小节） | `BeforeAfterReportTests` | 已实现 |
| 质量门 5：下游影响 + AI 日志 | `path_c.impact` 的 `ai_log` | `test_impact_records_ai_log_when_proven` | 已实现 |
| 质量门 6：flag 面板 + 截图双通道 | `path_c.flag` | `FlagTests` | 已实现 |
| 质量门 7：统一经 `collect_evidence.py` | `evidence.EvidenceWriter` | `EvidenceIntegrationTests`（真实落盘） | 已实现 |
| 校验标准 1：copy/paste 逐步复现 | 报告「复现命令」段 + `--noproxy '*'` | 人工复跑 infra-03 命令 | 已实现 |
| 校验标准 2：与 `report-exam` 兼容 | 共享容器格式（未自造格式） | `collect_evidence` 契约夹具 | 已实现 |
| 校验标准 3：三件套 + 术语规范 | `check_glossary.py` + 片段结构 | 47 废弃术语 0 命中 | 已实现 |
| 豁免 1：无基础设施面 → 记录依据后转技能 | `report.next_skills` + `ABSENT` 判定 | `test_absent_steps_produce_handoff_suggestion` | 已实现 |
| 豁免 2：配置错误部分生效 → 如实记录 | `cloud_misconfig` / `model_server` 的 `AUTH_REQUIRED` 分支 | `CloudTests` / `ContainerTests` | 已实现 |
| 豁免 3：被 RBAC/护栏拦截 → 记录不重试 | `privesc`/`container` 单次执行 + `BLOCKED(guardrail)` | `test_guardrail_block_is_blocked` | 已实现 |
| 豁免 4：疑似诱饵机 → ≤30 分钟结束 | `--decoy` 短路 + `--decoy-timebox`（默认 30） | `test_decoy_sends_zero_requests`、`test_decoy_timebox_stops_remaining_steps` | 已实现 |

| infra-02 示意脚本来源记录 | `provenance.SCRIPT_SOURCES["infra-02"]` → `--script-src` | `SkillClauseTests.test_provenance_covers_exactly_five_demo_script_steps`；infra-02 片段「脚本 / PoC」节含 AWS CLI 官方 URL | 已实现 |
| infra-03 示意脚本来源记录 | `provenance.SCRIPT_SOURCES["infra-03"]` | 同上；infra-03 片段含 vLLM 官方 URL | 已实现 |
| infra-04 示意脚本来源记录 | `provenance.SCRIPT_SOURCES["infra-04"]` | 同上；infra-04 片段含 kubectl 官方 URL | 已实现 |
| infra-05 示意脚本来源记录 | `provenance.SCRIPT_SOURCES["infra-05"]` | 同上；infra-05 片段含 LiteLLM 官方 URL | 已实现 |
| infra-06 示意脚本来源记录 | `provenance.SCRIPT_SOURCES["infra-06"]` | 同上；infra-06 片段含 kubelet 官方 URL | 已实现 |
| infra-05 以合法身份调用推理 | `path_b.gateway` + `--gateway-verify-endpoint` / `--gateway-credential-env` / `--allow-inference` | `GatewayLegalIdentityTests` 2 例；命令仅引用 `$GATEWAY_TOKEN`，凭据明文不入片段 | 已实现 |
| infra-06 模型服务 `/exec` 端点 | `path_c._exec_via_endpoint` + `--exec-endpoint` | `ExecEndpointTests` 3 例（成功 / 本机回显 / 被拒） | 已实现 |
| 质量门：截图含目标标识与时间戳 | `shot.ShotPlanner.plan(target=, timestamp=)` | `SkillClauseTests.test_shot_hook_carries_target_and_timestamp`；实测片段钩子含 `--target` 与 `--timestamp` | 已实现 |
| 执行体「未过质量门不得进入下一步」 | `runner.run` 在 `evidence_ok=False` 时 `break` 并留注记 | `SkillGateTests.test_evidence_failure_stops_following_steps` | 已实现 |
| 独立机证据不覆盖主目标 | `runner._scoped_output` 按目标建证据/截图子目录 | `SkillGateTests.test_secondary_target_writes_to_separate_dir` | 已实现 |

**核对结论**：SKILL.md 声明项 39 条，全部有实现位置与验证方式，遗漏 0。

## 2. 三层隔离与推送留痕（阶段 11）

检出锁（`scripts/checkout_lock.py --check`）在推送前返回非 0：`GLOSSARY.md` / `scripts/measure_coverage.py` / `scripts/check_token_budget.py` / `.github/workflows/ci.yml` 被多个 worktree 同时改动。按 ADR-0006 逐 hunk 核对并集：

| 并发方 | 其共享文件改动 | 与本分支是否重叠 | 结论 |
|---|---|---|---|
| `feat/attack-supply-chain-tools`（`D:/_sc_tools_wt`，HEAD `7b6aa02`） | 三个共享文件相对 `main` 共 6 插入 / 70 删除，逐 hunk 全为**删除态**（缺 RAG 术语块、预算上调注释、覆盖率目标）——`merge-base --is-ancestor main HEAD` 为假，基线落后 | **无新增内容需并集**；本分支已 `merge origin/main` 含全部内容 | 检出锁为保守误报，并发方需自行 rebase |

结论：本分支以 `git merge origin/main --no-ff` 取并集后，`git diff --name-status origin/main..HEAD` **无删除文件**，攻击面文件（含 `tools/attack_rag/`、`tools/inject_kb.py`）完整存在。并发方仅剩 `feat/attack-supply-chain-tools` 一个，且其差异全为落后基线的删除态，无任何待并入的新增内容。据此按 `pre-push` 钩子文档所列例外（`--no-verify`，前提为逐 hunk 确认并集无误）完成推送；本表为逐 hunk 核对留痕。

**推送通道**：SSH（`origin`）为首选，失败再试 HTTPS（`origin-https`），各一次即停（用户硬约定）。
