# attack-embeddings 阶段 3 `to-spec ②` 门禁记录 · 历史留痕回填

> 回溯核验：不表示原流程按序执行；判定依据见右列，均由现有产物或本次复跑支撑。

| 检查项 | 依据 | 实测摘要 | 判定 |
|---|---|---|---|
| 本阶段产物 | 主线 §3.3 | `docs/specs/attack-embeddings-spec-v2.md` 5197B：§1 AC-1..AC-11 布尔表、§3 门禁映射、§4 C-1..C-4 核实闸、§5 v1→v2 差异；同 issue #158 追加并保留 v1；Ch6 二次 to-spec 落 #275（12 条 AC-C） | 符合（回溯） |
| 上游复核 | 主线 §2.3 | `python -m unittest discover -s tests/attack_embeddings -t . -q` → Ran 77, OK；v1 七节未被改写（v2 §5 第 1 条声明） | 符合（回溯） |
| B1–B9 相关项 | 主线 §2.1 | B1/B2 与 v1 一致；B6 AC-9/AC-10 绑 CI S2；B7 AC-8 仅 emb-07 触 PyRIT 对象图；B8 每条 AC 有检查命令或人工判据 | 替代（回溯） |

**结论：PASS（回溯）**。证据指针：`docs/specs/attack-embeddings-spec-v2.md`、issue #158 / #275；提交 `8438894`。
