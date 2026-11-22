## Problem Statement
演练者在 Ch9 云场景中需要枚举 EC2/安全组暴露面并把模型服务器版本号关联到 CVE 查询，现有 recon-ai 7 步只做 AI 组件指纹，不含云网络暴露面与版本→CVE 提示。

## Solution
新增独立只读模块 `ch9_cloud_surface.py`：输入实例/SG/版本观测，输出暴露面判定与版本记录 + CVE 查询建议；不新增 step_id、不执行攻击、不爆破。

## User Stories
1. 作为演练者，我想识别公网 IP + 0.0.0.0/0 实例，以便定位暴露面。
2. 我想区分只读发现与主动探测，以便守边界。
3. 我想记录模型服务器版本，以便查 CVE。
4. 我想无数据时如实 ABSENT，以便不虚构。
5. 作为评审者，我想三件套证据，以便报告复用。
6. 作为编排者，我想不新增 step_id，以便兼容既有清单。

## Implementation Decisions
- 纯判定函数，经注入的观测数据工作，零网络在判定层。
- 不生成 CVE 利用载荷，只给查询建议与版本号。
- 不改动 probes/inventory/runner 既有判据。

## Testing Decisions
- 只测外部行为：观测 → 结论/暴露项/版本；覆盖命中/缺项/边界三路径。

## Out of Scope
- 不执行云 API 调用（由入口命令采集后传入）；不新增 step_id；不做主动探测。

## Further Notes
事实见 `docs/research/recon-ai-ch9-canonical.md`（R-1..R-4）。
