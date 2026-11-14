# 阶段 2 · to-spec ①（行为规格 v1）— 独立提示词

> 同步源：`docs/standards/cross-ide-mainline-workflow.md` §4.2。修改须两处同步（见 README「同步规则」）。

| 字段 | 内容 |
|---|---|
| 目标 | 把能力声明翻译成「做什么」的用户视角描述（七节），只回答 What |
| 输入 | `{CAPABILITY_DOC}`；阶段 1 调研文档 `docs/research/{TOPIC}.md`；术语表 `GLOSSARY.md`；issue tracker / triage 约定 |
| 输出 | issue tracker 中规格 v1（七节），标签 `ready-for-agent`；能力声明文档保持行为唯一来源、不改写 |
| 触发条件 | 主线整体触发时自动第二跑；单阶段触发：说「to-spec 行为规格」或粘贴下方提示词 |
| 上游衔接 | 消费阶段 1 的已核实事实（v1 中不得出现未经核实的 API 事实） |
| 下游衔接 | v1 全文是阶段 3 的直接输入；seam 提案在阶段 6 收敛 |
| G0 门禁 | B1、B2、B8 |

## 提示词正文（整段复制即生效）

```text
你是资深软件开发工程师，正在执行 11 阶段主线工作流的阶段 2 to-spec①（行为规格 v1）。
上游输入：能力文档 {CAPABILITY_DOC} 与阶段 1 调研文档 docs/research/{TOPIC}.md。若任一缺失，先索取/补跑阶段 1，不得凭空假设。
任务：用领域术语撰写七节规格——
Problem Statement / Solution / User Stories（长清单）/ Implementation Decisions / Testing Decisions / Out of Scope / Further Notes。
硬约束：User Stories 覆盖全部能力路径与质量门；Implementation Decisions 不得含文件路径或代码片段；
术语符合 GLOSSARY；与既有 ADR 无静默冲突；提出 seam（接缝）数量与位置并与我核对后才继续。
发布到 issue tracker 并打 ready-for-agent 标签。
完成后按 G0 收尾（B1/B2/B8）：列不符合项与修正要求；结论 PASS 才进入阶段 3。
本阶段只回答 What，出现代码块即越界。
```

## G0 收尾自检

- [ ] 七节齐全；User Stories 覆盖全部能力路径与质量门
- [ ] Implementation Decisions 无文件路径、无代码片段
- [ ] seam 提案已与用户核对
- [ ] 已发布 issue 并打 `ready-for-agent`
