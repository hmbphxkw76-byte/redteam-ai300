# 阶段 5 · triage（分类定级）— 独立提示词

> 同步源：`docs/standards/cross-ide-mainline-workflow.md` §4.5。修改须两处同步（见 README「同步规则」）。

| 字段 | 内容 |
|---|---|
| 目标 | 判定每张工单由 agent 还是人工承接，补齐 agent 就绪上下文 |
| 输入 | 阶段 4 产生的全部新工单；五标签映射（needs-triage / needs-info / ready-for-agent / ready-for-human / wontfix） |
| 输出 | 每张工单的规范标签与分类理由；`ready-for-agent` 工单的完整 brief（目标 / 输入 / 约束 / 验收 / 验证命令） |
| 触发条件 | 主线整体触发时自动第五跑；单阶段触发：说「triage 分类」或粘贴下方提示词 |
| 上游衔接 | 消费阶段 4 的工单集合（含验收条件与验证命令，brief 从中提炼） |
| 下游衔接 | `ready-for-agent` 工单 + brief 是阶段 8 实现的直接输入；`ready-for-human` 项须人工闭环后回流 |
| G0 门禁 | B8 |

## 提示词正文（整段复制即生效）

```text
你是资深软件开发工程师，正在执行 11 阶段主线工作流的阶段 5 triage。
上游输入：阶段 4 产生的全部新工单。若无工单，回退阶段 4。
任务：对每张工单判定由 agent 还是人工承接，按五标签状态机流转：
needs-triage / needs-info / ready-for-agent / ready-for-human / wontfix。
规则：需人工项（端点凭据、CI secrets、需手动交互/外部授权）标 ready-for-human 并记录依据；
信息不足标 needs-info 并列出所缺；为每张 ready-for-agent 工单写完整 brief：
目标 / 输入 / 约束 / 验收条件 / 验证命令（从工单与 v2 提炼，不新增语义）。
硬约束：每张工单恰有一个规范标签；ready-for-agent 必含完整 brief；结论留痕。
完成后按 G0 收尾（B8）：列不符合项与修正要求；结论 PASS 才进入阶段 6。
```

## G0 收尾自检

- [ ] 每张工单恰有一个规范标签，附分类理由
- [ ] 每个 `ready-for-agent` 工单含完整五要素 brief
- [ ] 人工项与 `ready-for-human` 一一对应并记录依据
- [ ] 分类结论已留痕（issue 评论或工单正文）
