## 变更摘要

<!-- 简述本次变更：新增/修改了哪个 agent 或 skill -->

## 纳管信息（新增组件必填，CI 将据此校验）

- **组件类型**：`skill` / `agent` / `文档` / `流水线`
- **对齐能力域**（D1–D11）：`例如 D3`
- **优先级**（P0/P1/P2）：`例如 P0`
- **目标计分单元**：`AI向量机 / 传统向量机 / 独立机 / 域控 / 通用`
- **端到端演示**（链接或说明）：`例如 演示产出合格证据的路径/截图`

## 治理合规自检

- [ ] 已按 §4.2 五要素解剖编写（front-matter 七字段 + 执行体/质量门/校验标准/失败与豁免）
- [ ] 已在 `GOVERNANCE.md` §4.4 登记（新增技能时）
- [ ] 术语符合 `GLOSSARY.md`（无 `_Avoid_` 废弃术语）
- [ ] 本地已通过：`python scripts/validate_skill.py && python scripts/check_glossary.py`
- [ ] 本地测试通过：`python -m pytest tests/ -q`
