# attack-infra 术语映射表

> **版本** v1.0 · **输入** 规格 v2（#213）、`docs/operations/attack-infra-design.md`、`GLOSSARY.md`
> **性质** 阶段 7 交付物：SKILL.md 概念 ↔ 一手源概念 ↔ 实现标识符的双向映射，消除代码/规格/报告间的语义漂移。

## 1. 映射表

| SKILL.md 概念 | 规范术语（GLOSSARY） | 一手源概念 | 实现标识符 | 定义要点 |
|---|---|---|---|---|
| 云 AI 平台 / 模型服务器 / 容器 / 推理网关 | **模型服务器**、**推理网关**（阶段 7 新增） | vLLM `/v1/models`（F-2）、Triton `v2/health/ready`（F-4）、Ollama `/api/tags`（F-9）、LiteLLM `/models`（F-5） | `fingerprint.PROBES`、`fingerprint.detect()`、`Endpoint.kind` | 服务类型由响应结构判定；端口只是候选 |
| 发现基础设施面（infra-01） | **模型服务器**（暴露面语义） | 三元组判据（canonical P-1） | `path_a.discover()`、`Finding` | 命中即归类；未命中记 `ABSENT(reason=spa_fallback/network)` |
| 云 AI 平台配置错误（infra-02） | **配置错误**（既有语义：误配导致越权可达） | AWS CLI `--no-sign-request`（F-8） | `path_a.cloud_misconfig()` | 匿名列举成功才算生效，被拒须留原始错误体 |
| 模型服务器暴露/滥用（infra-03） | **模型服务器** | OpenAI 兼容 `object:list`（F-10） | `path_a.model_server()`、`--allow-inference` | 列举 → `EXPOSED_NO_AUTH`；单次推理成功 → `EXPLOITED` |
| 容器化负载越权（infra-04） | **越权调用** | `kubectl auth can-i --list`（F-6）、`system:serviceaccount:<ns>:<sa>`（F-6） | `path_b.container()`、`CommandResult` | 授权面列举成功即判定；匿名 `403` 记 `AUTH_REQUIRED` |
| 推理网关凭据泄露（infra-05） | **推理网关**、**凭据指纹**（本实现口径，§2） | LiteLLM `config.yaml` 的 `api_key`（F-5） | `path_b.gateway()`、`CredentialHint(prefix,len,location)` | 只记指纹，明文不落片段 |
| 提权 → 意外代码执行（infra-06） | **代码执行**（ASI05） | `nodes/proxy` 的 `get` 可执行容器命令（F-8） | `path_c.privesc()` | 回显须来自目标主机；命本机判 `BLOCKED(local_echo)` |
| 下游影响取证（infra-07） | **证据片段** + AI 交互日志 | §6.3（`GOVERNANCE.md`）、F-16 | `path_c.impact()`、`before/after` | 两段响应差异非空才算证明 |
| flag 取证（infra-08） | **flag 双通道**（既有） | 面板值 == 截图值（F-16） | `path_c.flag()` | 不一致判 `BLOCKED` |
| 每步证据 | **证据片段** | `tools/collect_evidence.py`（F-17） | `evidence.EvidenceWriter.emit()` | 三件套/五件套由共享容器定义 |
| 判定结论 | **降级结论**（阶段 7 新增） | 本实现口径 | `model.Outcome` | 五值互斥，非 `EXPLOITED` 须附依据 |
| 失败与豁免 | **诱饵机**（既有） | `GLOSSARY.md` 诱饵机三信号 | `path_c` 早停分支、`runner` 零请求断言 | 命中后终止且不再发包 |

## 2. 需在实现层固定的三条口径

1. **凭据指纹**：`CredentialHint` 只含「算法前缀 + 长度 + 命中位置」。报告与片段中禁止出现完整值；同一凭据在多次命中时合并为一条（按 `prefix+length` 去重）。
2. **降级结论**：五值互斥且必须带 `reason`（允许值以 `tools/attack_infra/model.py` 常量为准，不在本文件重复枚举）：`ABSENT_REASONS` 四项、`BLOCKED_REASONS` 五项；`AUTH_REQUIRED` 使用 HTTP 权威原因（`http_401`/`http_403`/`forbidden`/`no_credential`）。
3. **端口与判据分离**：报告中的端口是「探测事实」，服务类型是「判定结论」；不得用端口反推类型（canonical P-3）。

## 3. ADR 影响

- 无新增 ADR：术语增补属 GLOSSARY 必要增量（ADR-0005「基线 + 必要增量」），预算 14918/15000 字节通过。
- 与 ADR-0006 的关系：`GLOSSARY.md` 属共享文件，推送前须过 `checkout_lock.py --check`；若与并行主线冲突，取并集后重跑 `check_token_budget.py --check`。

## 4. 门禁记录（阶段 7）

| 编号 | 检查项 | 依据 | 实测（命令 + 摘要） | 判定 | 结论 |
|---|---|---|---|---|---|
| B1 | 五要素未被术语增补破坏 | §2.1 | `python scripts/validate_skill.py` → 16 技能合规 | 符合 | PASS |
| B2 | 术语一致 | §2.1 | `python scripts/check_glossary.py` → 47 废弃术语 0 命中；新增 3 条含定义与来源 | 符合 | PASS |
| B8 | 可追溯性 | §2.1 | 每条映射带 canonical 编号；术语条目带来源路径 | 符合 | PASS |
| AC-① | 映射表覆盖全部新概念 | §3.7 验收① | 12 行覆盖 SKILL.md 8 步 + 质量门 + 豁免 | 符合 | PASS |
| AC-② | 条目含定义与来源 | 验收② | GLOSSARY 三条均含「来源：」行 | 符合 | PASS |
| AC-③ | `check_glossary` 通过 | 验收③ | 退出码 0 | 符合 | PASS |
| AC-④ | ADR 编号连续、冲突显式标注 | 验收④ | 无新增 ADR；ADR-0005/0006 关系于 §3 标注 | 符合 | PASS |

**阶段结论**：`PASS`（不符合项 0）。复验命令：`python scripts/check_glossary.py && python scripts/check_token_budget.py --check && python scripts/validate_skill.py`。
