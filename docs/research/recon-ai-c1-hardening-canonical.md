# recon-ai Ch9 C1 云暴露面加固事实索引

> **版本** v1.0 · **状态** 已核实 · **性质** 本轮加固单一可信源
> **取证日期** 2026-11-22 · **上游轻量版** `docs/research/recon-ai-ch9-canonical.md`（R-1..R-4，保留）
> **框架组合（矩阵 ⑥）** garak 首扫 + Kali 侦察 + 许可 AI；只读优先。

## 0. 结论
1. C1 覆盖三类只读观察：EC2 实例/SG ingress 暴露面（Listing 29-30）、未鉴权模型端点探测（Listing 31）、版本号→CVE 关联（Listing 32）。轻量版（PR #366）缺 Listing 31，且返回裸 dict、无七字段对齐、无 ≥90% 门槛。
2. 本轮升级为类型化 `C1Verdict` + 三类判定 + 七字段资产清单无损对齐；全程被动优先、`--profile active` 才追加定向端口（≤8）、只读、不执行攻击/不落明文凭据。
3. 不新增 step_id：C1 三判定作为 `recon-01`（LLM 引擎识别）的云侧旁路观测，不改 recon-01..07 判据与七字段契约。

## 1. 已核实清单

| # | 事实 | 来源 |
|---|---|---|
| C1-1 | `describe-security-groups` 描述 SG；`IpPermissions` = 入站规则，`CidrIp=0.0.0.0/0` 为「允许所有地址」；`-1` 协议=所有端口 | <https://docs.aws.amazon.com/cli/latest/reference/ec2/describe-security-groups.html>（一手，取证 2026-11-22） |
| C1-2 | `describe-instances` 只读列举实例与 PublicIp | 课程 Listing 29；矩阵 ⑥ Kali/云 CLI |
| C1-3 | 未鉴权模型端点（无 token 返回 200 + 模型元数据）属暴露面；探测只读、不绕过鉴权 | 课程 Listing 31；既有 probe recon-02 同语义 |
| C1-4 | CVE-2025-23266：NVIDIA Container Toolkit ≤1.17.7 / GPU Operator ≤25.3.0，CWE-426，CNA CVSS 3.1=9.0 CRITICAL | <https://nvd.nist.gov/vuln/detail/CVE-2025-23266>（一手，取证 2026-11-22） |
| C1-5 | 资产清单七字段契约 `asset_id/category/product/version/endpoint/credential_hint/evidence_step` | 本仓 `tools/recon_ai/model.py:99-108`（一手） |
| C1-6 | 被动优先；active 才追加定向端口，`MAX_ACTIVE_PORTS=8`，禁全扫描 | 本仓 `tools/recon_ai/policy.py:7,10,29`；`probes.py:324` |
| C1-7 | 只读不落明文凭据；框架组合 ⑥ | `docs/research/osai-skill-framework-matrix.md` ⑥ |

## 2. 三类判定映射

| Listing | 判定 | 成功判据 | 失败分支 |
|---|---|---|---|
| 29-30 | `analyze_instance` | PublicIp + `0.0.0.0/0` ingress → EXPOSED_NO_AUTH + 端口 | 无公网/仅私网 CIDR → ABSENT |
| 31 | `probe_unauth_endpoint` | 无鉴权头返回 200 且响应含模型/版本元数据 → EXPOSED_NO_AUTH | 401/403 → AUTH_REQUIRED；无响应 → ABSENT |
| 32 | `correlate_version` | 版本字符串 → 记录版本 + NVD 查询建议（含 CVE-2025-23266 锚点） | 无有效版本 → ABSENT |

## 3. 判据前提与陷阱
- **P-1 类型化**：`C1Verdict`（frozen + `__getitem__`/dict shim）。
- **P-2 只读边界**：判定层零网络零命令调用；命令字符串仅为数据；不落明文凭据（credential_hint 只留前缀/占位）。
- **P-3 七字段无损**：C1 判定可映射为七字段资产（category=MODEL_SERVICE/LLM_ENGINE，credential_hint 只指纹），不改 `Asset`/`ASSET_FIELDS`。
- **P-4 不新增 step_id**：作为 recon-01 旁路观测留痕，不改 recon-01..07。

## 4. 待核实 / 已排除
- **R-1**：端点是否真正未鉴权须由运行时代理观测确认，本模块只判传入响应；不阻断。
- **D-1**：不执行攻击载荷、不全端口扫描、不落明文、不新增 step_id。

## 5. 门禁记录（阶段 1）

| 编号 | 本阶段变更项 | 判定 | 复验命令 | 结论 |
|---|---|---|---|---|
| B7 | C1-7 零 AI 框架参与判定 | 符合 | `grep -rnE "pyrit\.orchestrator|Orchestrator|AzureOpenAIChatTarget" tools/recon_ai/ch9_c1*.py tools/recon_ai/ch9_cloud_surface.py` → 无 | PASS |
| B8 | C1-1..C1-7 带来源 | 符合 | `grep -c "https://\|本仓\|矩阵\|课程" docs/research/recon-ai-c1-hardening-canonical.md` | PASS |
| B9 | 框架组合 ⑥ | 符合 | `sed -n '79,83p' docs/research/osai-skill-framework-matrix.md` | PASS |

**阶段结论**：`PASS`。复验：`python scripts/check_glossary.py && python scripts/validate_skill.py`。
