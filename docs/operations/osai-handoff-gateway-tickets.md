# osai-handoff-gateway 工单与分类（阶段 4–5）

## 工单（垂直切片）

| ID | 标题 | 验收条件 | 阻塞边 | 验证命令 |
|---|---|---|---|---|
| T-1 | 共享值与交接索引类型 | AC-8 | 无 | `unittest test_handoff.py` |
| T-2 | panel_flags 派生（H3） | AC-4 | T-1 | `unittest -k panel` |
| T-3 | 侦察片段映射（H5） | AC-6 | T-1 | `unittest -k recon` |
| T-4 | 提交门禁 H6（断图/时间锚/加密） | AC-7 | T-1 | `unittest -k submission` |
| T-5 | H1/H2/H4 校验 | AC-1/2/3/5 | T-1 | `unittest -k handoff` |
| T-6 | 对齐矩阵断言 | AC-9/10/11/12 | T-2..T-5 | `unittest -k alignment` |

依赖图：T-1 → {T-2, T-3, T-4, T-5} → T-6，无环。

## 分类（阶段 5）

- T-1..T-6 全部 `ready-for-agent`：纯本地文件与标准库，无需真实端点或凭据。
- 无 `ready-for-human` 项：本阶段不含 flag 提交、目标连接、不可逆操作。
- 无 `needs-info` 项：所有输入格式已由一手源契约锚定。
