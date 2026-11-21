# attack-rag Ch6 复用侧差距调研（一手源指针）

> 版本 v1.0 · 2026-11-21 · 主线阶段 1（复用已核实事实，C3/T6 不重复检索）
> 一手源锚点：`D:\视频\OffSec   AI-300 Advanced AI Red Teaming\Ch6-Attacking-Embeddings.html` §6.2 Listing 8（inference_probing.py），本地课件可直接定位。
> 边界：本调研只覆盖「供 Ch6 inference probing 复用的 RAG 查询接口」，不扩展 attack-rag 的投毒主题。

## 1. 差距与一手源映射

| 差距（Ch6 对照） | 一手源（课程 HTML） | attack-rag 侧职责 | 非职责 |
|---|---|---|---|
| inference probing 需 RAG chat 查询接口（发查询→得响应文本） | 课程 Ch6 §6.2 Listing 8（inference_probing.py 三策略查询） | 把既有 `RagHarness.retrieve` + `Backend.respond` 适配成 `query_iface(prompt)->text` 注入接口 | 实现 probing 评分/top5_avg（归 attack-embeddings PR #309） |
| 检索片段来源（响应分段比对用） | 课程 Ch6 §6.2 Listing 8（多粒度分段） | 暴露检索上下文文本，供下游分段 | 分段与相似度计算 |

现有可复用点（`tools/attack_rag/`，本 worktree 可追溯）：
- `retrieval_probe.py` `RetrievalProbe.capture(query, stage, k) -> TopKTable`（检索观测面）
- `backends.py` `respond(query, context_texts) -> str`（LLM 响应接口，需 pyrit+端点）

## 2. 已排除

- 不新增投毒/检索操纵语义（非 Ch6 差距）；不 import 未合并的 attack-embeddings 代码。
- 课程 lab（megacorpone.ai）≠ AIVP，属环境差异，不判缺陷。

## 3. G0 门禁

| 编号 | 检查项 | 实测 | 判定 |
|---|---|---|---|
| B7/B8 | 一手源锚点 + 现有实现可追溯 | 课程 Listing 8 + 2 个本仓接口锚点 | 符合 |
| B9 | 框架组合（矩阵③ attack-rag：PyRIT+PoisonedRAG+自定义）不变 | 无偏离 | 符合 |

**结论：PASS**。
