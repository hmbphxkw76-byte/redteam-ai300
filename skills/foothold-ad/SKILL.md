---
name: foothold-ad
priority: P0
domain: D1
scoring_unit: 域控
trigger: foothold-traditional 已取得域内立足点并按 trad-08 移交（域内主机会话 + 可用凭据 + 可达域控），需进行域级升级与域控收敛
input: trad-08 立足点移交清单（会话/凭据指纹/路由/战利品索引）、recon-ai 资产清单（域控与证书服务地址）、离线工件（目录导出、模板导出、ACL 导出、信任列表）
output: 每步「命令 + 输出 + 截图」证据、域级攻击路径图、凭证指纹清单、proof.txt 双通道取证、report-exam 可无损消费的片段
---

# foothold-ad — AD 域渗透与域控收敛

承接 `foothold-traditional` 的立足点移交，处理**域域内立足点之后**的域级升级：Kerberos 可攻击账户、ADCS 模板、目录复制权限、域信任滥用，直至域控 `proof.txt`。不重做入口利用、本地提权与主机横向（属 `foothold-traditional` trad-01..10，判据不动）。

课程锚点：Ch11 §0.2（三域森林）、§2 S5–S9（域/信任/双归属/策略收口）、§3.6（ACL 决策表）、§4.2（10 步路径第 5–10 步）。设计依据见 `docs/operations/foothold-ad-design.md`。

## 执行体

按 ad-01 → ad-08 顺序推进；每步经 `tools/collect_evidence.py --strict` 落盘，未过质量门不得进入下一步。判据取值域沿用既有五值（`EXPLOITED` / `EXPOSED_NO_AUTH` / `AUTH_REQUIRED` / `ABSENT` / `BLOCKED`），无法判定记 `UNDETERMINED` 并在分析注记写明依据，不新造取值。

**语境门（前置）**：先判定语境——`course-capstone`（Ch11 课件：域管目标 + 3 个定格式问答）或 `osai-rehearsal`（计分演练：按计分单元产出）。语境不明记 `UNDETERMINED`，`proof.txt` 仅在 `course-capstone` 下作为硬要求。

### 前置：接收立足点

1. 读取 trad-08 移交清单，确认三项前置：域内主机会话、可用凭据（含指纹）、可达域控地址（Ch11 §3.1 地址规划）。缺任一项即 `BLOCKED` 并回退 `foothold-traditional`，不自行重做入口。
2. 复核 ACL 决策表（Ch11 §3.6）中本次动作方向的放行条目；无对应放行条目即阻断，不做跨区越权尝试。
3. **无真实环境时**先出采集清单：`python -m tools.foothold_ad.cli preflight --artifacts <ARTIFACT_DIR>`，按输出在真实域采集工件，再执行 `cli verify` 校验来源与完整性。纯静态生成，不生成样本、不伪造输出。

### ad-01 域环境测绘与信任枚举

1. 枚举根域与子域、域控地址、信任方向与 SID 过滤状态。
2. 命令：`ldapsearch -H ldap://<DC> -x -s base -b "" defaultNamingContext; nltest /domain_trusts /all_trusts /v`
3. 证据：`python tools/collect_evidence.py --step ad-01 --cmd "<实测命令>" --output-file loot/ad-01.txt --out loot/ad-01.md --shot-cmd "screenshot --region ad01" --target <DC> --strict`
4. 判据：三域（`megacorpone.ai` / `dmz.megacorpone.ai` / `dev.megacorpone.ai`）与信任方向齐备即成表；字段缺失记 `UNDETERMINED`，不按默认值推断。

### ad-02 Kerberos 可攻击账户枚举

1. 从目录导出中筛三类：有 SPN 且启用（Kerberoast 面）、`DONT_REQ_PREAUTH`（AS-REP 面）、非约束委派。
2. 命令：`python -m tools.foothold_ad.cli analyze --artifacts <ARTIFACT_DIR> --steps ad-02`
3. 证据：`python tools/collect_evidence.py --step ad-02 --cmd "<实测命令>" --output-file loot/ad-02.txt --out loot/ad-02.md --shot-cmd "screenshot --region ad02" --target <DOMAIN> --strict`
4. 判据：三类各自成表且含账户名与所属域；空集记 `ABSENT` 并给出筛选依据。

### ad-03 票据获取（Kerberoast / AS-REP）

1. 对 ad-02 命中账户取票据；记录加密类型（`rc4` / `aes256`）与工单号。
2. 命令：`impacket-GetUserSPNs <DOMAIN>/<USER>:<PASS> -dc-ip <DC> -request -outputfile loot/kerb.txt`
3. 证据：`python tools/collect_evidence.py --step ad-03 --cmd "<实测命令>" --output-file loot/ad-03.txt --out loot/ad-03.md --shot-cmd "screenshot --region ad03" --target <DC> --strict`
4. 判据：取得票据哈希且加密类型可判即成链（`EXPLOITED`）；被拒按 `NOT_VULNERABLE` 记录依据，不重放同一载荷。

### ad-04 ADCS 模板利用面判定

1. 枚举证书模板与注册端点，判定两类：ESC1（可控主体 + 客户端认证 EKU + 低权可注册 + 无需审批）、ESC8（HTTP 注册端点可中继）。
2. 命令：`certipy find -u <USER>@<DOMAIN> -p <PASS> -dc-ip <DC> -json -output loot/certipy`
3. 证据：`python tools/collect_evidence.py --step ad-04 --cmd "<实测命令>" --output-file loot/ad-04.txt --out loot/ad-04.md --shot-cmd "screenshot --region ad04" --target <CA_HOST> --strict`
4. 判据：ESC1 需同时满足「无审批 + 无授权签名 + 可控主体 + 客户端认证 EKU + 低权可注册」；ESC8 需「HTTP 注册端点 + EPA 未启用」。任一字段缺失记 `UNDETERMINED`；未命中记 `ABSENT` 并说明探测范围。

### ad-05 目录复制权限（DCSync 面）

1. 从 ACL 导出筛非 DC 主体对域对象持有的复制权限：`DS-Replication-Get-Changes` 与 `DS-Replication-Get-Changes-All`。
2. 命令：`python -m tools.foothold_ad.cli analyze --artifacts <ARTIFACT_DIR> --steps ad-05`
3. 证据：`python tools/collect_evidence.py --step ad-05 --cmd "<实测命令>" --output-file loot/ad-05.txt --out loot/ad-05.md --shot-cmd "screenshot --region ad05" --target <DOMAIN> --strict`
4. 判据：仅 `Get-Changes-All` 判成链；仅 `Get-Changes` 记部分能力并说明不足以复制凭据。

### ad-06 域信任滥用路径

1. 结合 ad-01 信任与跨域组成员，判定跨域高权主体或 SID 过滤关闭。
2. 命令：`python -m tools.foothold_ad.cli analyze --artifacts <ARTIFACT_DIR> --steps ad-06`
3. 证据：`python tools/collect_evidence.py --step ad-06 --cmd "<实测命令>" --output-file loot/ad-06.txt --out loot/ad-06.md --shot-cmd "screenshot --region ad06" --target <TRUST_TARGET> --strict`
4. 判据：双向可传递信任 + 跨域高权主体（或 SID 过滤关闭）同时成立才算路径成立；单条成立记 `EXPOSED_NO_AUTH` 并说明缺项。

### ad-07 域控收敛与 proof.txt 取证

1. 以 ad-03..ad-06 任一路径取得域控访问，读取 `proof.txt`（路径随课程给定）。
2. 命令：`whoami; id; type C:\proof.txt`（或对应平台等价物），与访问证明同屏。
3. 证据：`python tools/collect_evidence.py --step ad-07 --cmd "<实测命令>" --output-file loot/ad-07.txt --out loot/ad-07.md --shot-cmd "screenshot --region proof" --flag-panel "<面板提交值>" --flag-shot "<截图原值>" --target <DC> --strict`
4. 判据：`whoami`/`id` 与 `proof.txt` 同屏；面板提交值与截图原值逐字一致（§6.2 双通道）。单次提交约束见 `verify-evidence` 的 `proof-single`。

### ad-08 路径沉淀与移交

1. 输出域级路径图（立足点 → 票据/模板/复制/信任 → 域控），并登记凭据指纹与工单。
2. 命令：`python -m tools.foothold_ad.cli analyze --artifacts <ARTIFACT_DIR> --steps ad-08`
3. 证据：`python tools/collect_evidence.py --step ad-08 --cmd "<实测命令>" --output-file loot/ad-08.txt --out loot/ad-08.md --shot-cmd "screenshot --region path" --target <DOMAIN> --strict`
4. 判据：路径图可被 `report-exam` 的 High-Level Attack Path 直接引用；凭据索引与 `loot-manage` loot-01..05 一一对应，无游离条目。

## 无真实环境下的证据纪律

1. **夹具验证 ≠ 环境实测**：离线工件跑出的结论只能表述为「夹具验证」，报告与对话中不得写成环境实测。
2. **禁止占位结论**：无工件即 `BLOCKED`，字段缺失即 `UNDETERMINED`，不得用「未发现风险」代替「无法判定」。
3. **工件须可追溯**：`directory/templates/trusts`（及可选 `tickets/proof`）须在 `artifact_manifest.json` 登记 `sha256` / 采集工具与版本 / 采集时间 / 操作者；`provenance.ok=false` 的工件不得作为证据提交。
4. **schema 不受支持即停**：`schema_version` 主版本不符时该步记 `UNDETERMINED`，不按旧格式强解。
5. **可复现**：同一工件集合重复执行须得到同一 `digest`；结论与工件哈希同存，使「结论 ↔ 工件」双向可追。

## 质量门

以下证据**必须**全部产出，缺失任一即判定未过门禁，不得进入下一技能：

- 每步**确切命令**（可直接 copy/paste）与**关键输出**；第三方工具须附来源与版本，示意命令不得伪造回显。
- 每步**截图**（访问证明，含目标标识与时间戳）。
- **凭据指纹**：哈希仅存算法 + 前 8 位 + 长度 + 位置；任何输出中不得出现明文口令或完整哈希。
- **ad-07 双通道一致**：面板提交值等于截图/正文原值，且 `whoami`/`id` 同屏。
- **ad-01/ad-06 的 `UNDETERMINED` 依据**：字段缺失时写明缺哪一项，不以默认值代替。
- 每步证据统一经 `tools/collect_evidence.py` 产出，保证与 `report-exam` 的 Attack Walkthrough 兼容并可无损复用。
- **来源完整性**：`python -m tools.foothold_ad.cli verify --artifacts <ARTIFACT_DIR>` 退出码 0；`provenance.ok=false` 时工件不得作为证据，缺清单须先补建。
- 每个取得的票据、凭据指纹与 flag 已即时登记 `loot-manage`。

## 校验标准

- 攻击过程可被技术读者 **copy/paste 逐步复现**（§6.1），自研脚本附 sha256 与来源。
- `python -m unittest discover -s tests/foothold_ad -t .` 通过；新包覆盖率 ≥90%。
- `cli verify` 对完整工件退出码 0、对篡改工件退出码 1；`cli preflight` 输出含缺失项、采集命令与期望字段。
- 判据函数对同一工件集合**输出确定性一致**（同输入同 `digest`，无随机、无网络）。
- 名称术语符合 `GLOSSARY.md`（「域信任」「目录复制」「票据」「模板利用」「域控收敛」），禁用 `_Avoid_` 废弃术语。
- 证据片段结构对齐 `docs/contracts/collect_evidence.contract.md` §4；不改写节标题与 flag fenced 原值块。

## 失败与豁免

- **无工件 / 无域环境**：记 `BLOCKED` 并列缺失文件名与路径，不生成占位结论、不伪造回显；真实环境采集前先跑 `cli preflight` 取清单。
- **工件损坏或超限**（非 UTF-8 / 非 JSON / 超过 32MiB）：记 `BLOCKED` 并在注记保留解析错误，不尝试修复后强解。
- **schema 版本不支持**：该步记 `UNDETERMINED` 并写明版本，不按旧格式解析、不静默降级。
- **工件来源不可信**（清单缺失、哈希不符、字段不全）：判据可出，但该证据不得提交；先补齐 `artifact_manifest.json` 再复核。
- **字段缺失**（如无 SID 过滤状态）：记 `UNDETERMINED` 并写明缺口，不按默认值推断为「安全」或「不安全」。
- **票据被拒**：记 `NOT_VULNERABLE` 与拒绝原因（策略/加密类型不匹配），不反复重试同一载荷。
- **ADCS 无注册端点**：记 `ABSENT` 并说明探测范围，不将「未发现」写成「不存在」。
- **跨域动作无 ACL 放行**：即时阻断并记录条目缺失，不绕行既有区际策略。
- **疑似诱饵域控**：0 分或与资产清单不符时，记录依据后移交 `decoy-detect` 判定，≤30 分钟结束。
- **语境冲突**：`osai-rehearsal` 下无 `proof.txt` 要求，按计分单元（AI向量机/传统向量机/独立机）产出，不把课程目标当考试要求。

> 主线：`docs/operations/skill-mainline-workflow.md`（C1/C8：11 阶段、to-spec 两遍、G0）。当前状态为**可执行增量**，阶段 1–11 待补，见设计文档 §9；`capstone-rehearse` 中只能记 `PARTIAL`。
