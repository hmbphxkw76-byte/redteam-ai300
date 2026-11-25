---
name: foothold-traditional
priority: P0
domain: D1
scoring_unit: 传统向量机
trigger: recon-ai 传统面枚举完成，需取得攻击链公网入口立足点、内网横向与本地提权（2 条攻击链 × 3 台链式主机，含 2 台传统向量机）
input: recon-ai 资产清单（外部入口、服务版本、初始访问向量）、已获取凭据（可选）
output: 每台主机「命令 + 输出 + 截图」证据、横向路径图、提权前后权限证明、trad_vector.txt flag 取证、面向 AI 向量机的立足点移交清单
---

# foothold-traditional — 传统入口/横向/提权

获取传统攻击链立足点：**公网入口利用 → 本地提权 → 内网横向 → 链式主机收敛**。对齐能力域 D1 + 传统渗透技术（经典枚举、利用、横向、提权），覆盖 2 条攻击链 × 3 台链式主机，认领其中 **2 台传统向量机（10 分/台）**，并为 4 台 AI向量机与独立机供给内网可达性（立足点移交）。本技能同时承担「链式入口」职责：任一链的初始立足点是后续全部 AI 向量利用的前置（§4.5 流水线第三站）。目标 flag 文件为 `trad_vector.txt`。

## 执行体

按「入口利用 → 首台提权取证 → 内网横向 → 次台提权取证 → 路径沉淀与移交」顺序推进，每步经 `tools/collect_evidence.py` 落盘证据，未过质量门不得进入下一步。每取得一个凭据、会话或 flag，**必须**即时登记至 `loot-manage`（§5.2），禁止散落于对话上下文。

### 前置：入口攻击面复核

1. 复用 `recon-ai` 传统面枚举结果，选定单链公网入口（每条攻击链自单一公网入口起始），确认服务版本与初始访问向量。
2. 与 `threat-model` 输出的优先攻击路径对齐；对疑似诱饵机的入口先做判定（`decoy-detect`），不盲打。

### 阶段一 — 入口利用（取得初始立足点）

1. **trad-01 复核入口攻击面**：对选定公网入口做针对性服务枚举，确认版本与可达 exploit 面。
   - 命令：`nmap -sV -sC -p- <ENTRY_IP>`
   - 证据：`python tools/collect_evidence.py --step trad-01 --cmd "nmap -sV -sC -p- <ENTRY_IP>" --out loot/trad-01-entry-recon.md --shot-cmd "screenshot --region nmap_entry" --target <ENTRY_IP> --strict`
2. **trad-02 公网入口利用**：以版本对应 exploit 取得初始立足点（shell/会话）；第三方 exploit **必须**附来源链接或代码副本及修改说明（§6.1）。
   - 命令：`msfconsole -q -x "use <ENTRY_EXPLOIT>; set RHOSTS <ENTRY_IP>; run"`
   - 证据：`python tools/collect_evidence.py --step trad-02 --cmd "msfconsole -q -x 'use <ENTRY_EXPLOIT>; set RHOSTS <ENTRY_IP>; run'" --out loot/trad-02-initial-foothold.md --shot-cmd "screenshot --region shell_proof" --target <ENTRY_IP> --strict`

### 阶段二 — 首台主机提权与取证

1. **trad-03 首台主机本地提权**：枚举提权面（sudo、SUID、内核、计划任务、服务错配）并利用；**前后权限证明同屏**（提权前 `id` 与提权后 `id` 对照）。
   - 命令：`sudo -l; find / -perm -4000 -type f 2>/dev/null; id && <PRIVESC_CMD> && id`
   - 证据：`python tools/collect_evidence.py --step trad-03 --cmd "sudo -l; find / -perm -4000 -type f 2>/dev/null; id && <PRIVESC_CMD> && id" --out loot/trad-03-privesc-host1.md --shot-cmd "screenshot --region privesc_before_after" --target <CHAIN1_HOST1> --strict`
2. **trad-04 首台传统向量机 flag 取证**：定位并读取 `trad_vector.txt`，取证含访问证明（`whoami`/`id` + flag 内容同屏），双通道一致（控制面板提交值 == 报告截图/正文，§6.2）；取得后即时登记 `loot-manage`。
   - 命令：`whoami; id; find / -name trad_vector.txt 2>/dev/null -exec cat {} \;`
   - 证据：`python tools/collect_evidence.py --step trad-04 --cmd "whoami; id; find / -name trad_vector.txt 2>/dev/null -exec cat {} \;" --out loot/trad-04-flag-host1.md --shot-cmd "screenshot --region flag_proof" --flag "<trad_vector.txt 值>" --target <TRAD_VECTOR_HOST1> --strict`

### 阶段三 — 内网横向与次台主机收敛

1. **trad-05 内网横向枚举与路径发现**：自首台主机做内网枚举（跨网段路由/pivot），识别通往次台链式主机与 AI 向量机的最短路径。
   - 命令：`proxychains nmap -sV -p- <INTERNAL_NET>`
   - 证据：`python tools/collect_evidence.py --step trad-05 --cmd "proxychains nmap -sV -p- <INTERNAL_NET>" --out loot/trad-05-internal-recon.md --shot-cmd "screenshot --region internal_nmap" --target <INTERNAL_NET> --strict`
2. **trad-06 横向至次台链式主机**：复用已登记战利品（凭据/会话/密钥）横向移动，优先凭据复用而非重新爆破；横向凭据来源引用 `loot-manage` 登记项。
   - 命令：`ssh <USER>@<CHAIN1_HOST2> -i <LOOTED_KEY>`
   - 证据：`python tools/collect_evidence.py --step trad-06 --cmd "ssh <USER>@<CHAIN1_HOST2> -i <LOOTED_KEY>" --out loot/trad-06-lateral-host2.md --shot-cmd "screenshot --region lateral_session" --target <CHAIN1_HOST2> --strict`
3. **trad-07 次台传统向量机提权 + flag 取证**：在次台重复提权流程（前后权限证明）并取得第二个 `trad_vector.txt`（10 分）；完成后按 `threat-model` 路径向链内 AI向量机或第二攻击链延伸。
   - 命令：`sudo -l && <PRIVESC_CMD> && id; find / -name trad_vector.txt 2>/dev/null -exec cat {} \;`
   - 证据：`python tools/collect_evidence.py --step trad-07 --cmd "sudo -l && <PRIVESC_CMD> && id; find / -name trad_vector.txt 2>/dev/null -exec cat {} \;" --out loot/trad-07-flag-host2.md --shot-cmd "screenshot --region flag_proof" --flag "<trad_vector.txt 值>" --target <TRAD_VECTOR_HOST2> --strict`

#### 可选手法条目（Ch11 传统手法库，按需引用）

以下为 trad-03/trad-07 的可选具体手法，每条含前置条件、示意命令（标注 Ch11 来源，不伪造回显）与清理引用（复用共享变更登记契约，C1）：

- **RDS Gateway pivot**（trad-03，[D:L540]）：前置=已入 VPN Users 组、有 RDP 凭据；`xfreerdp3 /v:CONNECT02 /g:<GW>:443 /u:<USER> /p:<PASS>` + `\tsclient\payloads` 共享投放（Ch11 §11.4）。
- **CVE-2025-26125 本地提权**（trad-03，[D:L586]）：前置=取得 CLIENT01 低权 shell；按 Listing 26 提权至 SYSTEM，前后 `id` 同屏。
- **进程内存转储取凭据**（trad-07，[D:L1143]）：前置=目标进程含解密后凭据（如 KeePass）；`procdump -ma <PID> dump.dmp` → 离线搜明文，procdump 为签名工具不易触发 Defender（Ch11 Listing 51）。
- **计划任务二进制替换提权**（trad-07，[D:L1424]）：前置=计划任务路径用户可写；`icacls <task.exe>` 确认可写 → 替换为载荷 → 待任务以 SYSTEM 运行，取证 SYSTEM shell（Ch11 §11.4）。
- **GitLab PAT / 硬编码凭据发现**（trad-05，[D:L615-734]）：前置=取得 dev 主机访问；查 GitLab PAT、dev 分支配置、SSMS 插件硬编码凭据，登记 `loot-manage`（路径引用，不复制）。
- 上述改动系统/放模块的手法，清理状态字段复用共享变更登记契约（C1）；示意命令标来源、不伪造目标回显。

### 收尾 — 路径沉淀与立足点移交

1. **trad-08 横向路径图沉淀 + 立足点移交**：输出横向路径图（入口 → 各主机 → 汇聚方向，供 Executive Summary 的 High-Level Attack Path 复用），并产出「立足点移交清单」：会话/凭据、可达 AI向量机与独立机的路由、已登记战利品索引，显式满足 `attack-ai-agent` / `attack-rag` / `attack-mcp-tool` 的内网立足点前置（§4.5）。
   - 命令：`python tools/collect_evidence.py --step trad-08 --cmd "echo '横向路径图 + 立足点移交清单（见 loot/attack-path.md 与 loot/handoff.md）'" --out loot/trad-08-handoff.md --shot-cmd "screenshot --region path_graph" --target <ATTACK_CHAIN> --strict`
2. 两台传统向量机均取证后，链内剩余主机为 AI向量机时移交 AI 向量技能；域控收敛由编排层按需触发（非本技能范围）。

## Ch9 入口扩展（加固版，不改 trad-01..08 判据）

事实源 `docs/research/foothold-traditional-ch9-hardening-canonical.md`（H-1..H-6），课程锚点 Listing 1-2 / 56-63。类型化五值结论 `tools/foothold_traditional/ch9_model.py#TriadVerdict`，判据入口 `tools/foothold_traditional/ch9_entry.py#ssrf_credential_entry` 与 `tools/foothold_traditional/ch9_entry.py#gpu_foothold_entry`，strict 证据 `tools/foothold_traditional/ch9_evidence.py#emit_strict_evidence`（参数组装 `tools/foothold_traditional/ch9_evidence.py#build_evidence_argv`），编排 `tools/foothold_traditional/ch9_runner.py#run_ch9`：

| 步骤 | 能力 | 一手事实 | 课程锚点 |
|---|---|---|---|
| trad-09 | `/api/export?template_url=file:///proc/self/environ` SSRF 响应识别 Lambda env 凭据键名（`AWS_ACCESS_KEY_ID`/`AWS_SECRET_ACCESS_KEY`/`AWS_SESSION_TOKEN`），仅产 `Fingerprint`（键名+长度+位置），可选 `GetCallerIdentity` 验证 | H-1/H-2 | L1-2 |
| trad-10 | `sudo -l` 识别 `(root) NOPASSWD:` 包装脚本，作为 GPU 逃逸初始立足点；提权本体由 attack-infra ch9-gpu 承担 | H-3 | L56-63 |

**能力边界**：不生成 SSRF 载荷、不执行 CVE-2025-23266 提权（P-4）、不引入 AI 框架（矩阵 ⑦）；凭据明文一律不落 output/证据（P-1）；每步经 `collect_evidence.py --strict` 落盘三件套（H-6）。复验：`python scripts/verify_skill_refs.py && python scripts/verify_ch9_ft_coverage.py --min 90`。

## 质量门

以下证据**必须**全部产出，缺失任一即判定未过门禁，不得进入下一技能：

- 每个攻击步骤的**确切命令**（可直接 copy/paste）。
- 每步骤的**关键输出**（含利用成功、提权前后权限、横向会话建立回显）。
- 每步骤的**截图**（访问证明，含目标标识与时间戳）。
- **提权前后权限证明**（`whoami`/`id` 对照，§7.2）。
- **横向路径图**（入口 → 横向 → 各主机的路径证据链）。
- 2 台传统向量机 `trad_vector.txt` 的「面板提交 + 截图」**双通道一致**。
- 上述每步证据统一通过共享工具 `tools/collect_evidence.py` 产出（对齐 GOVERNANCE §质量门），保证三件套/五件套结构稳定、与 `report-exam` 的 Attack Walkthrough 兼容、并可由 CI 校验。关键输出运行期须注入 `--output-file`（`docs/contracts/collect_evidence.contract.md` §1）。
- 每个取得的凭据/会话/flag 已即时登记 `loot-manage`。

## 校验标准

- 攻击过程可被技术读者 **copy/paste 逐步复现**（§6.1）；第三方 exploit 附来源与修改说明。
- 每主机小节满足 **§7.2 五段式**：枚举（暴露攻击面）、漏洞描述与完整利用、提权（前后权限证明）、flag 取证。
- 证据结构与 `report-exam` 的 Attack Walkthrough 小节直接兼容，可**无损复用**，无需二次整理。
- 术语符合 `GLOSSARY.md`（用「传统向量机」「攻击链」「链式入口」「诱饵机」等规范词，禁用 `_Avoid_` 废弃术语）。

## 失败与豁免

- 若公网入口不可利用（版本无对应 exploit、被拦截），记录判定依据后换入口/换攻击链，不长时间盲试；两条链均不可达时上报编排层重估 `threat-model` 路径。
- 若本地提权失败，如实以当前权限继续横向并记录限制，不夸大权限状态；提权缺口汇总至 `capstone-rehearse` 缺口清单。
- 若次台主机实为 AI向量机（非传统向量），记录判定依据后移交对应 AI 向量技能，不越界实施 AI 特定利用。
- 若目标为疑似诱饵机（0 分、故意无漏洞），记录判定依据后 ≤30 分钟内主动放弃并记录理由（§5.3），不在 0 分主机空耗。
