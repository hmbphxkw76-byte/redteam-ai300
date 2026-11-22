## Problem Statement
演练者面对 Ch9 云侧场景时，缺少从公网入口 SSRF 泄漏环境变量提取云凭据的初始访问手法；面对 GPU 主机场景时，缺少从受限账号枚举 sudo 包装脚本的立足点前段。现有 foothold-traditional 只覆盖 nmap/msf 入口与本地 sudo/SUID 提权，不含这两类入口。

## Solution
新增两个可选步骤：SSRF 凭据入口（从响应文本识别 AWS 凭据键名并只产指纹）、GPU 立足点枚举（从 sudo -l 输出识别 NOPASSWD 包装脚本）。沿用 collect_evidence 三件套与五值结论，(payload 执行与提权本体不在此技能)。

## User Stories
1. 作为演练者，我想从 SSRF 响应中识别 AWS 凭据键名，以便确认初始访问入口。
2. 作为演练者，我想凭据只记指纹，以便不落明文。
3. 作为演练者，我想验证凭据身份，以便确认可用性。
4. 作为演练者，我想从 sudo -l 输出识别 NOPASSWD 脚本，以便定位 GPU 提权入口。
5. 作为演练者，我想无入口时如实降级，以便不夸大立足点。
6. 作为评审者，我想每步有三件套证据，以便报告复用。

## Implementation Decisions
- 新增独立模块，经 RunContext 单 seam 注入命令执行。
- 凭据仅产前缀/长度/位置指纹；明文不进 output。
- 不实现 SSRF 载荷生成（由 recon 提供入口）与 CVE 提权本体（由 attack-infra 提供）。
- 五值结论，reason 沿用既有枚举集合。

## Testing Decisions
- 只测外部行为：ctx → verdict.outcome/reason/指纹/命令。
- FakeCommand 离线夹具；覆盖成功/缺键名/被拒三路径。
- 断言无明文凭据落 output。

## Out of Scope
- 不生成 SSRF 利用载荷；不实现 GPU CVE 提权执行；不改动 trad-01..08 判据。
- 不引入 PyRIT 或任何 AI 框架。

## Further Notes
事实见 `docs/research/foothold-traditional-ch9-canonical.md`（T-1..T-4）。
