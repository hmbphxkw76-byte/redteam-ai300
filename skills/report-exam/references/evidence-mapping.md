# 现有 evidence → 报告章节 映射协议

> 配套 `skills/report-exam/SKILL.md` §4。本文件把本仓库既有证据产物与 S1 报告章节做**确定性绑定**，使报告组装可机读、可复核、无损复用。

## A. 证据产物清单（当前仓库）

| 路径 | 来源技能 | 形态 | 现状 |
|---|---|---|---|
| `evidence/attack-ai-agent-real/aia-01.md` … `aia-12.md` | `attack-ai-agent` | `collect_evidence.py` 片段（五件套/三件套） | 真实目标主机 `http://192.168.40.189/api/labs/MM_0x/chat`；**flag 双通道均为「未提供」** |
| `evidence/attack-ai-agent/aia-*.md` | `attack-ai-agent` | 同上 | 演练/仿真；非 OSAI 正式考试 |
| `loot/registry.md` | `loot-manage` | 战利品登记簿（单一事实源） | 当前未生成（需在实战流水线中产生） |
| `tools/collect_evidence.py` | 通用 | 证据片段渲染器 | 已就位（CI 校验一致） |

## B. 片段 → 小节 映射规则

| 片段特征 | 落入报告位置 |
|---|---|
| `recon-*` / 含端口扫描、服务探测 | 对应主机 `#### Initial Access / Exploitation` 之「枚举」段 |
| `attack-ai-agent` / `aia-*` | AI 向量主机 `#### Initial Access / Exploitation`（提示注入/记忆/工具滥用）；prompt/payload 在此 |
| `attack-rag` / `attack-mcp-tool` / `attack-embeddings` 等 | 各自计分主机的利用段 |
| `foothold-traditional` / `trad-*` | 传统向量机 / 链式入口的利用与横向段 |
| 含 `#### flag 取证（双通道一致）` 的片段 | 对应主机 `#### Proof` 段 |
| 含 `#### AI 交互日志` 的片段 | 正文对应段 **且** Appendix D 全量复制 |
| 长 PoC / 第三方脚本 | Appendix A（正文留指引） |

## C. 当前 real 证据的具体落位（示例）

`evidence/attack-ai-agent-real/aia-01.md`（I/O 通道 + 系统提示 + 护栏基线枚举）：

- **落位 1**：Standalone / AI-vector host → `#### Initial Access / Exploitation` 的"枚举"子段（agent 攻击面盘点）。
- **落位 2**：Appendix D「AI 会话/提示历史」（其 `#### AI 交互日志` 全量复制）。

`aia-02..aia-12.md`（利用步骤）：按 step 顺序归入同一主机的"漏洞描述与完整利用"段；若某步为提权则入 `#### Privilege Escalation`，若含 flag 则入 `#### Proof`。

> 注意：当前仅覆盖 **1 个 AI 向量主机**级别的真实证据，未触及 Chain 1/2 其余主机、域控、独立机与诱饵机。正式考试需按 B 表补齐 8 计分目标 + 2 诱饵机的证据，缺者如实记"未达成"。

## D. 组装命令（引用方式 §3.2）

```bash
# 单机小节：直接 include 该主机全部片段（无损）
mkdir -p report
for f in evidence/attack-ai-agent-real/aia-*.md; do
  echo "" >> report/standalone-ai.md
  cat "$f" >> report/standalone-ai.md
done

# Appendix D：抽取所有 AI 交互日志
: > report/appendix-ai-history.md
for f in evidence/attack-ai-agent-real/aia-*.md; do
  sed -n '/#### AI 交互日志/,/#### 证据校验/p' "$f" >> report/appendix-ai-history.md
done

# 双通道一致性：比对面板值 vs 报告 flag 值（交给 verify-evidence vrf-04）
```

## E. 一致性约束

- 片段内 `#### 证据校验（五件套 / 三件套）` 表的"状态"列须全为"已提供"（三件套）/ 可选项如实；缺失项回溯补录，禁止文字替代截图。
- 报告内 IPv4、端口、版本、时间戳、请求数、结果须与片段逐字一致（双版亦同）。
- 域控 `proof.txt` 在报告中仅出现一次提交记录（§2.2）。
