# OSAI 八计分目标映射表（演练模板 · 非提交件）

> **性质**：单一事实源（C1）。其他文档与脚本只写本表路径锚点，不复制表体。
> **依据**：`docs/governance/GOVERNANCE.md:54-63`（4 AI×15 + 2 传统×10 + 独立机 15 + 域控 5 = 100）；快照 §3 `L46-56`（DC flag 仅提交一次）。
> **填写纪律**：仅在真实考试窗口内由考生填写；本表不含真实 flag、OSID 或截图字节。未填项保持「待考试窗口填写」。

| 目标ID | 分值 | 类型 | 技能 | 证据片段 | flag状态 | 报告小节 | 状态 |
|---|---:|---|---|---|---|---|---|
| T1 | 15 | AI向量 | attack-ai-agent | evidence/attack-ai-agent-real/aia-01.md | 待取证 | §T1 | 未就绪 |
| T2 | 15 | AI向量 | attack-mcp-tool | evidence/attack-mcp-tool/mcp-01.md | 待取证 | §T2 | 未就绪 |
| T3 | 15 | AI向量 | attack-rag | 待考试窗口填写 | 待取证 | §T3 | 未就绪 |
| T4 | 15 | AI向量 | attack-embeddings | 待考试窗口填写 | 待取证 | §T4 | 未就绪 |
| T5 | 15 | 独立机 | attack-infra | 待考试窗口填写 | 待取证 | §T5 | 未就绪 |
| T6 | 10 | 传统向量 | foothold-traditional | 待考试窗口填写 | 待取证 | §T6 | 未就绪 |
| T7 | 10 | 传统向量 | foothold-traditional | 待考试窗口填写 | 待取证 | §T7 | 未就绪 |
| T8 | 5 | 域控 | foothold-traditional | 待考试窗口填写 | 待提交一次 | §T8 | 未就绪 |

## 只读校验

```bash
python tools/evidence_pipeline.py --target-map docs/operations/osai-target-map.md --root .
```

退出码 0 表示八目标证据与双通道齐备；1 表示存在缺口并逐行打印路径。脚本**只读**，不生成截图、flag 或报告。
