# recon-ai Ch6 侦察侧差距调研（一手源指针）

> 版本 v1.0 · 日期 2026-11-21 · 性质：主线阶段 1（复用已核实一手源，C3/T6 不重复检索）
> 边界：recon-ai 只读、不导出、不上传（SKILL.md §功能边界 4）；Ch6 的向量导出/probing **执行**属 attack-embeddings（PR #309，已实现）。本调研只覆盖侦察侧可复用元数据。

## 1. 差距与一手源映射

| 差距（Ch6 对照） | 一手源（课程 HTML，本任务唯一文档依据） | recon-ai 侧职责 | 非职责（归 attack-embeddings，PR #309） |
|---|---|---|---|
| 维度指纹 → 模型候选 | 课程 Ch6 §6.2 Listing 5–7（维度→模型对照表） | recon-04 记录向量库维度（若被动/主动面可得）写入资产元数据；不可得记「不可判定」 | 用候选做反演/模型推断 |
| 可导出面声明 | 课程 Ch6 §6.2 Listing 3（Weaviate GraphQL 导出脚本） | 资产清单标注向量库「可导出面」与端口（复用 probes.py recon-04 声明） | 实际导出 .npy/.csv/.parquet |
| probing 入口声明 | 课程 Ch6 §6.2 Listing 8（inference_probing.py） | recon-03/07 记录 RAG chat 接口存在性供下游复用 | 发送 probing 查询并评分 |

> attack-embeddings 侧实现属**并行 PR #309**（尚未合并，不在本 worktree），此处仅作归属说明，不作为可 import 的路径指针。

## 2. 已知排除

- AIVP 无独立 embedding 反演 lab（课程 lab ≠ AIVP，属环境差异）；recon-ai 不因此判为缺陷。
- recon-ai 不改「只读」边界：维度若不可得记「不可判定」，不臆测模型。

## 3. G0 门禁（阶段 1）

| 编号 | 检查项 | 实测 | 判定 |
|---|---|---|---|
| B7/B8 | 一手源可追溯（指针到已核实文档/课程 Listing） | 3 差距均附锚点 | 符合 |
| B9 | 框架组合（矩阵⑥ recon-ai：garak+Kali+AI；本次仅元数据层，无框架偏离） | 组合不变 | 符合 |

**结论：PASS**。
