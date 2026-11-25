# 技能与工具全量验证报告（2026-11-25）

> 验证对象：`http://192.168.40.183:9000`（DVAA）、`http://192.168.40.189/explore`（AIVP）、K8s 控制节点 `192.168.40.189`（含 GitLab / Harbor / ArgoCD / Monitoring 等部署）。
> 基线提交：`7f5fe0dde3399d2e180b988c41795f89b87343c9`（main，工作区干净）。

## 1. 结论

| 维度 | 结论 | 关键依据 |
|---|---|---|
| 三目标连通性 | PASS | 两个 HTTP 服务 200；集群 3/3 节点 Ready，API Server v1.37.2 |
| 20 个技能结构合规 | PASS | `validate_skill.py` 20/20 合规 |
| 工具可编译 | PASS | 302 文件，失败 0（修正后，原 285） |
| 单元与集成测试 | PASS | 1596 例通过、1 跳过、退出码 0 |
| 覆盖率 | PASS | 88.1%（门槛 80%） |
| 真实目标联调 | PASS | recon-ai 两目标 C1–C12 全 PASS（含截图） |
| 发现缺陷 | 5 项，全部已修并回归 | D1–D5 |
| 目标侧配置问题 | 4 项，仅记录未改动 | S1–S4（只读边界） |
| 通用适配性 | PASS | 新增目标仅追加画像 JSON，核心代码零改动 |

## 2. 方法与边界

1. 目标字面量一律经 `tools/target_profile.py` 的 `TargetProfile` 注入：真实值置于 gitignored 的 `tools/target_profiles.local.json`，经 `REDTEAM_TARGET_PROFILES` / `REDTEAM_TARGET_PROFILE` 选择。
2. 对目标**只读**：仅发送侦察、枚举、单次无害回显类请求；不执行写入型攻击动作，不改动集群与服务端配置。
3. 修复范围限本项目代码、测试、清单与文档；目标侧问题只记录根因与修复建议。
4. 不以放宽断言、跳过测试或改判缺陷的方式取得 PASS。

## 3. 目标连通性与基础可用性

| 目标 | 识别结果 | 关键探测 | 判定 |
|---|---|---|---|
| `192.168.40.183:9000` | DVAA（Damn Vulnerable AI Agent，OpenA2A），21 agent | `/health` 200（`status=ok,agents=21`）；`/api/llm/status` 200（LongCat-2.5）；`/api/agents/helperbot/chat` 200 JSON 回显 | PASS |
| `192.168.40.189:80` | AIVP（AI Vulnerabilities Playground），nginx/1.27.5，SPA | `/explore` 200；`/api/config` 200（`llm_model_default=LongCat-2.5`）；`/api/me/runs?limit=1` 200 | PASS |
| `192.168.40.189`（K8s） | v1.37.2，containerd 2.4.2，3 节点 | `kubectl get nodes` 3/3 Ready；17 个 namespace；API Server 版本与客户端一致 | PASS |

**重要观测**：两个 HTTP 目标对未知路径均返回 `200 + text/html`（SPA 回退页）。DVAA 的 `/mcp/tools`、`/api/config`（无该端点时）与 AIVP 的 `/v1/models`、`/assets/index.js` 均命中回退页。任何仅按状态码判定的检查都会产生**假阳性**；本项目已有 `probes.is_spa_fallback` 判据（200 + html + doctype），实测该判据正确将 `/v1/models` 记为「不存在」。

## 4. 集群部署应用验证

| 命名空间 | 组件 | 端点实测 | 结论 |
|---|---|---|---|
| gitlab | webservice 1/1、sidekiq 3/3、gitaly、minio、postgresql、redis | `:30080/-/readiness` 200、`:30080/users/sign_in` 200 | PASS（外部 URL `host: 192.168.40.189, port: 30080` 与实际暴露一致） |
| harbor | core/registry/portal/jobservice/nginx 均 1/1 | `https://:30003/api/v2.0/health` 200 | 可用；HTTP 入口见 S1 |
| argocd | server、repo-server、controller、redis | `:30700` → 307 → `https://:30701` 200；3 个 Application 全 Synced/Healthy | PASS |
| monitoring | prometheus、grafana、kube-state-metrics、node-exporter | `:30907/login` 200；`:30909/-/ready` 200 | PASS |
| ingress-nginx | controller 1/1 | `:30081/` 404（无默认后端，符合预期）；`argocd.lan` 经此入站 | PASS |
| nginx-gateway / ai-weekly | Gateway `ai-weekly` PROGRAMMED=True | `ai-weekly.<LB-IP>.nip.io` 200；裸 IP 404（按 Host 路由，符合 Gateway API 语义） | PASS |
| kube-system / flannel / metallb / cert-manager | 系统面 | 全部 Ready；证书 `argocd-server-tls` READY | PASS |

**Pod 状态分布**：Running 67、ContainerStatusUnknown 26、Completed 9、Error 2。非 Running 集中在 `ai-weekly`（历史副本集孤儿）与 `gitlab/postgresql`（曾因节点 ephemeral-storage 驱逐）。当前三节点 `DiskPressure/MemoryPressure/PIDPressure` 均为 False，业务 Deployment 就绪数与期望一致。

## 5. 技能与工具验证矩阵

技能结构校验：`validate_skill.py` 20/20 合规；`check_glossary.py` PASS（66 条废弃术语零命中）。
主线留痕校验：`validate_skill_mainline.py` 7 PASS / 13 GAP。GAP 均为**流程留痕债务**（缺 `docs/specs` v1/v2、阶段门禁记录 0/10），非功能失效；CI 以非 `--strict` 运行，不阻断。

| 技能 | 代码入口 | 验证方式 | 结论 |
|---|---|---|---|
| recon-ai | `tools.recon_ai.cli` | 真实目标 ×2（AIVP、DVAA），7 步 + 截图 | PASS（C1–C12） |
| attack-mcp-tool | `tools.attack_mcp_tool.cli` | mcp-01 真实目标；26 例单测 | PASS（修复后） |
| attack-rag | `tools.attack_rag.cli` | rag-00 消费真实 recon 清单 | PASS |
| attack-ai-agent | `tools.attack_ai_agent.demo` / `run_real` | 离线闭环 aia-01..12 | PASS |
| attack-jailbreak | `tools.attack_jailbreak.demo` | 离线 10/10 成功 | PASS |
| attack-supply-chain | 各步骤模块（sc-*） | `pickle_bypass --list`（133 gadgets）+ 单测 | PASS |
| attack-embeddings | `tools.attack_embeddings.cli` | 离线 8 步实跑（7 完全生效 / 1 部分生效） | PASS |
| attack-infra | `tools.attack_infra.cli` | `--dry-run` 装配 8 步且零请求（未做真实利用） | PASS |
| attack-multi-agent / attack-multimodal | `cli.py` / 步骤模块 | CLI 可执行 + 单测 | PASS（未做真实目标写入） |
| capstone-rehearse | `tools.capstone_rehearse.cli` | `--stdout` 六步走查与耗时细分输出 | PASS |
| tooling-automate / threat-model | `cli.py` | CLI 可执行 + 单测（threat-model 离线产出模型） | PASS |
| decoy-detect | `tools.decoy_detect.cli run` | 合成清单实跑（判定/放弃理由齐全） | PASS |
| loot-manage | `tools.loot_manage` | `init` + `validate`（列/行/类型/状态/ID/主机六项 OK） | PASS |
| report-exam | `python -m tools.report_exam` | `index` 对非考试证据片段集合优雅降级（8 主机、空片段、退出 0） | PASS |
| verify-evidence | `python -m tools.verify_evidence` | 对 recon 证据片段实跑，输出 blocking/missing 分类 | PASS |
| osai-exam-orchestrator | `python -m tools.osai_orchestrator --plan` | 12 项能力域 dry-run | PASS |
| foothold-ad / foothold-traditional | `tools.foothold_ad.cli plan` / 人工 SOP + `collect_evidence` | 8 步计划输出；`trad-*` 为人工步骤（文档给出确切命令与取证） | PASS（设计如此，无 SMB/域环境） |

工具可执行性：13 个 `cli.py` 包全部 `--help` 退出 0；7 个包按设计以 `demo.py` / 单步骤模块为入口（SKILL.md 已载明），`--help` 同样退出 0。顶层 22 个脚本 `--help` 全部退出 0。

## 6. 缺陷、根因与修复

| ID | 现象 | 根因（文件:行） | 修复 | 回归证据 |
|---|---|---|---|---|
| D1 | 侦察生成 `/favicon.ico/_stcore/health`、`/site.webmanifest/_stcore/health` 等伪基路径 | `tools/recon_ai/discovery.py:134` 以静态扩展名白名单过滤，`.ico`/`.webmanifest` 未覆盖 | 改为通用判据：末段含 `.` 即静态文件 | 新增 2 例；仅保留 `/chat` 类目录候选 |
| D2 | 非 Vite 布局漏采前端产物，回落默认 `/assets/index.js`（SPA 回退 200） | `tools/recon_ai/probes.py:24` 正则硬限定 `/assets/` 前缀与双引号 | 改为任意 `<script src="*.js">`（双/单引号）+ `urljoin` 绝对化 | DVAA 实跑采集到 `/js/app.js` |
| D3 | 画像缺角色映射时把 `<LAB_ID>` 字面量拼进 URL 外发 | `tools/recon_ai/runner.py` 拼 URL 后无占位符守卫 | 发送前校验 `<LAB_ID>/<TARGET>/<MODEL>`，命中即记「已跳过」 | DVAA 实跑记为「已跳过：画像未提供该角色映射」 |
| D4 | MCP 工具面被误判「已跳过」，而回答中已列 2 个工具 | `tools/attack_mcp_tool/model.py:26` 仅认「工具名：」标签；`_SERVER_RE` 只认 `Server ID:` | 增加「项目符号 + 名 + 声明字段」行内形态；接受裸 `Server:` | mcp-01 由「已跳过」转为「完全生效」，枚举到工具 |
| D5 | CI 编译清单漏登记 17 个文件（含 `tools/foothold_traditional/` 整包、`evidence_pipeline.py`、11 个 `verify_*` 脚本） | `scripts/tools_manifest.json` 未随新增文件更新 | 补齐 packages/scripts 条目 | 编译文件 285→302，`--check-missing` 归零 |

修复后回归：`python -m unittest discover -s tests -t .` 1596 例通过（1 跳过）；`validate_skill` / `check_glossary` / `check_token_budget --check` / `check_contract_manifest` / `check_contract_consumers` / `check_evidence_contract` 全部 PASS；覆盖率 88.1%。

## 7. 目标侧问题（只读记录，未改动）

| ID | 问题 | 根因 | 建议 |
|---|---|---|---|
| S1 | Harbor HTTP 入口 `:30002` 301 到 `https://192.168.40.189/`（丢端口）→ 落到宿主机 443 的另一 nginx → 404 | harbor-nginx 以 `$host` 重定向，未带 `$server_port`；externalURL 未含端口 | 统一以 `:30003` 对外，或 egress 重定向带端口；修正 externalURL |
| S2 | `ai-weekly` 26 个 ContainerStatusUnknown 孤儿 + 2 个 Error | 节点曾 ephemeral-storage 压力导致副本驱逐，旧副本集未回收 | 清理 Failed/Unknown pod，配置 ephemeral-storage 配额与告警 |
| S3 | `gitlab-runner` 重启 11 次、sidekiq 探针失败历史 | 节点重启窗口内探针超时，非配置错误 | 观察；必要时放宽 startupProbe |
| S4 | 两个 Web 目标对未知路径返回 200 + SPA HTML | 前端 history 路由回退 | 已由 `is_spa_fallback` 判据覆盖；对接新目标时不得只判状态码 |

另：`tools/target_profiles.local.json` 的 `extra.smb_hosts` 仍指向与本环境无关的主机（`*.biogenai.corp`、`10.10.x`）。foothold 类技能据此会产生无效目标，建议清理或改为实际演练值（属本地数据，未擅改）。

## 8. 通用适配性说明

1. **单一事实源**：所有目标字面量只存在于画像；`tools/`、`scripts/`、`skills/`、配置层实测零命中（`git grep` 空结果），18 份文档中的 IP 仅为历史验证记录。
2. **零代码切换已实测**：本轮仅在本地画像追加 `dvaa-rehearsal` 一条（`host`/`model`/`labs`/`endpoints`），核心代码未改一行，DVAA 即完成 7 步侦察并 C1–C12 全 PASS；AIVP 与 DVAA 使用同一套代码与同一份步骤定义。
3. **端点差异由画像吸收**：AIVP 有 `/explore` 与 `/api/labs/{lab}/chat`；DVAA 无 `/explore`、聊天面为 `/api/agents/{id}/chat`。后者由 `agent_chat` 模板 + `family=dvaa` 发现逻辑处理，未写死任何目标分支。
4. **发现优于假设**：前端产物路径按实际 `<script src>` 解析（D2 修复后不再假设 `/assets/`），基路径按目录形态推导（D1），角色缺失即如实记「不可判定」（D3）。
5. **扩展路径**：新增同类目标 = 新增一份画像 JSON（`name`、`host`、`model`、`labs`、可选 `endpoints`），无需改动代码、测试或步骤定义；画像目录支持一次加载多份，按名选择。

## 9. 未覆盖项与残余风险

1. 破坏性步骤未对真实目标执行：`mcp-02..mcp-11`、`rag-01..rag-05`、`sc-*` 投放类、`trad-*` 利用类仅以单测与离线 demo 覆盖（按只读边界刻意排除）。
2. `foothold-ad` / `foothold-traditional` 需域控与 SMB 环境，当前集群无对应资产，仅验证计划输出与 SOP 完整性。
3. `validate_skill_mainline.py` 的 13 项 GAP 未补齐：补齐需对每个技能重跑 to-spec 两遍与 10 份阶段门禁记录，超出本次验证范围，属流程债务。
4. `python -m tools.osai_orchestrator.cli` / `tools.tooling_automate.cli` 触发 `RuntimeWarning`（包 `__init__` 已导入 `cli`）；按文档以 `python -m tools.osai_orchestrator` 调用无告警，未改动以免影响既有导入路径。
5. 覆盖率 88.1% 为全量口径；新增 9 例测试已计入。

## 10. 复现命令

```bash
# 静态门禁
python scripts/validate_skill.py && python scripts/check_glossary.py
python scripts/check_token_budget.py --check
python scripts/check_tools_compile.py --check-missing
python -m unittest discover -s tests -t . -q

# 双目标侦察（画像驱动，验证通用性）
REDTEAM_TARGET_PROFILES=tools/target_profiles.local.json \
REDTEAM_TARGET_PROFILE=aivp-rehearsal \
python -m tools.recon_ai.cli run --target http://<TARGET> --profile passive --json

# 单步联调
python -m tools.attack_rag.cli --target http://<TARGET> --backend fake \
  --step rag-00 --recon-inventory evidence/recon-ai/ai-assets.json --no-emit --json
python -m tools.attack_mcp_tool.cli --target http://<TARGET> --mode agent-sse \
  --step mcp-01 --no-emit --no-shot --json
```

产物位置：`evidence/verification/recon-aivp-shot/`、`recon-dvaa-shot/`（各含 7 份片段、7 张截图、MANIFEST 与 verification.json）。
