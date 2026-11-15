# 威胁模型（threat-model）— 192.168.40.189

> 规划产出，不含实际攻击利用；所有结论由对应攻击子技能在实战中验证。
> 资产可被下游按 `asset_id` 直接复用（衔接 report-exam / verify-evidence / decoy-detect）。

## 1. 资产计分排序（杠杆优先）

| 排名 | 资产ID | 计分分类 | 分值 | 攻击面 | 证据 step |
|---|---|---|---|---|---|
| 1 | `ai-llm-a-01` | AI向量机 | 15 | D3 | `loot/recon-01-llm-engine.md` |
| 2 | `ai-rag-b-01` | 独立机 | 15 | D5 | `loot/recon-03-rag-lib.md` |
| 3 | `vec-c-01` | AI向量机 | 15 | D6 | `loot/recon-04-vector-db.md` |
| 4 | `trad-d-01` | 传统向量机 | 10 | D1 | `loot/recon-07-guardrail.md` |
| 5 | `dc-e-01` | 域控 | 5 | D1 | `loot/recon-07-guardrail.md` |
| 6 | `decoy-f-01` | 诱饵机 | 0 | — | `loot/recon-07-guardrail.md` |

## 2. 信任边界与最短攻击路径

**信任边界**（可达性分层）：

| 信任域 | 资产 |
|---|---|
| 内网 | `ai-llm-a-01`、`vec-c-01`、`dc-e-01` |
| 独立可达 | `ai-rag-b-01` |
| 公网入口 | `trad-d-01` |
| 未分类 | `decoy-f-01` |

**最短攻击路径**（起止 / 阶段 / 耗时 / 依赖子技能 / 可达性）：

| 目标资产 | 起点 | 必经阶段 | 耗时 | 依赖子技能 | 可达性 |
|---|---|---|---|---|---|
| `ai-llm-a-01` | `trad-d-01` | 入口 → 横向 → 提权 → AI利用 → flag | 90min | attack-ai-agent、attack-rag、attack-mcp-tool | 可达 |
| `ai-rag-b-01` | `（直接可达）` | 入口 → 横向 → 提权 → AI利用 → flag | 90min | attack-mcp-tool | 可达 |
| `vec-c-01` | `trad-d-01` | 入口 → 横向 → 提权 → AI利用 → flag | 90min | attack-ai-agent、attack-rag、attack-mcp-tool | 可达 |

## 3. 诱饵判定清单（时间盒 ≤30min）

| 资产ID | 判定 | 三维度命中 | 耗时 | 放弃 | 依据 | 时间戳 |
|---|---|---|---|---|---|---|
| `decoy-f-01` | 诱饵机 | 3/3 | 12min | 是 | 无 AI 面、无高价值服务、枚举反馈过干净 | 2026-11-15T11:04:53+08:00 |

## 4. 优先级攻击图（驱动 §4.5 编排）

- **根节点（最高杠杆）**：`ai-llm-a-01`、`ai-rag-b-01`、`vec-c-01`
- **节点**：`ai-llm-a-01`、`ai-rag-b-01`、`vec-c-01`、`trad-d-01`、`dc-e-01`
- **排除的诱饵机**：`decoy-f-01`
- **边（最短路径）**：
  - `trad-d-01` → `ai-llm-a-01`（可达）
  - `（直接可达）` → `ai-rag-b-01`（可达）
  - `trad-d-01` → `vec-c-01`（可达）
- **编排顺序（§4.5）**：`ai-llm-a-01` → `ai-rag-b-01` → `vec-c-01` → `trad-d-01` → `dc-e-01`

## 质量门

**四项齐全**：高价值资产清单 / 信任边界+最短攻击路径 / 诱饵判定清单 / 优先级攻击图。

