## Problem Statement

既有 `foothold-traditional` 的 Ch9 轻量版（PR #357）虽能识别 SSRF 响应中的 AWS 凭据键名与 `sudo -l` 包装脚本，但以裸 `dict` 返回、未接入 `collect_evidence.py --strict` 证据落盘、无类型化五值结论，覆盖率未达本轮要求的 ≥90%。演练者因此无法获得可复现、可评分的原子证据，编排层也无法按既有五值语义降级转技能。

## Solution

在既有 `tools/foothold_traditional/ch9_entry.py` 之上加固为类型化实现：定义 `TriadVerdict` 五值结论类型（含 `step_id/outcome/reason/summary/command/output/shot_cmd/fingerprints`），新增证据发射器按 `collect_evidence.py --strict` 落盘每步三件套；SSRF 入口只产指纹（`AWS_ACCESS_KEY_ID/SECRET_ACCESS_KEY/SESSION_TOKEN` 键名+长度+位置，明文不落盘），GPU 立足点只判 NOPASSWD 包装脚本存在性，不执行 CVE-2025-23266 载荷。

## User Stories

1. 作为演练者，我想从 `/api/export?template_url=file:///proc/self/environ` 的响应识别 Lambda 环境变量中的 AWS 凭据键名，以便确认初始访问入口。
2. 作为演练者，我想凭据只记指纹（键名/长度/位置），以便不把明文带入证据与报告。
3. 作为演练者，我想用 `GetCallerIdentity` 验证凭据身份，以便确认其可用性与影响半径。
4. 作为演练者，我想从 `sudo -l` 输出识别 `(root) NOPASSWD:` 包装脚本，以便定位 GPU 逃逸的初始立足点。
5. 作为演练者，我想在无权/无工具/无键名时得到五值结论之一，以便编排层正确转技能。
6. 作为演练者，我想每步经 `collect_evidence.py --strict` 落盘三件套，以便报告无损复用。
7. 作为评审者，我想每步命令可直接复制粘贴且含截图钩子，以便复核。
8. 作为编排者，我想新模块与既有 trad-01..08 判据零交叉，以便零回归。
9. 作为评审者，我想 SKILL.md 引用的每个工具/模块字面完整，以便按端到端演示复核。
10. 作为质量门负责人，我想新增模块行覆盖率 ≥90%，以便满足本轮门槛。

## Implementation Decisions

- 新增 `TriadVerdict` dataclass（五值 outcome + 既有 reason 集合 + 证据字段），不改既有 `tools/attack_infra` 类型。
- 保留 `ch9_entry.py` 的公开函数签名，返回类型改为 `TriadVerdict`（DUCK-TYPING 到 `collect_evidence` 参数）。
- 新增 `emit_strict_evidence(verdict, ctx)` 薄封装：组装 `collect_evidence.py --step <id> --cmd <command> --output <text> --shot-cmd <hook> --strict` 参数列表，经注入的命令执行器调用；失败以 `evidence_ok=False` 标记（不抛异常）。
- 凭据处理：`_redact` 先替换所有 AWS_* 值，output 只保留脱敏文本；fingerprints 只含 `(键名, 长度, 位置)`。
- GPU 立足点只判 `sudo -l` 的 NOPASSWD 包装脚本；`gpu_escape` 判据引用 attack-infra canonical C-9，不实现载荷。
- 不改动 trad-01..08 步骤表、SKILL.md 既有判据、GLOSSARY 既有术语。

## Testing Decisions

- 好测试只断言外部行为：给定 ctx → verdict 字段（outcome/reason/指纹/命令/输出）+ 证据 CLI 参数，不测私有辅助函数。
- 新增测试覆盖：SSRF 命中/无键名/被拒/明文不落盘/身份验证 5 路径；GPU 命中/无脚本/无工具 3 路径；证据 strict 成功与失败 2 路径。
- 覆盖率用 `scripts/measure_coverage.py` 的 tracer 逻辑复现，目标 ≥90%（本轮门槛高于 CI 全局 80%）。

## Out of Scope

- 不实现 SSRF 载荷生成（入口由调用方采集后传入）。
- 不执行 CVE-2025-23266 提权载荷（属 attack-infra ch9-gpu）。
- 不改动既有 trad-01..08、flag 双通道、report-exam 逻辑。
- 不引入 PyRIT 或任何 AI 框架（框架矩阵 ⑦）。

## Further Notes

- 事实见 `docs/research/foothold-traditional-ch9-hardening-canonical.md`（H-1..H-6、P-1..P-4、R-1、D-1）。
- 上游轻量版事实 `docs/research/foothold-traditional-ch9-canonical.md` 保留，本轮只升级实现质量。
