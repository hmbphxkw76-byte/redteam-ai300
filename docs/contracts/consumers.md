# 契约消费者登记表

> **性质**：单一事实源（`AGENTS.md` C1）。登记每个 `tools/collect_evidence.py` 契约消费者及其依赖的契约元素；契约元素名以 `docs/contracts/collect_evidence.contract.md` 为准。
> **维护规则**：新技能落地消费共享工具时新增一行（状态 `未合入`）；合入 `main` 后改状态为 `已合入`。改动共享工具契约时，须保证所有消费者的「依赖契约元素」仍在清单中出现（由 `scripts/check_contract_consumers.py` 断言）。
> **依赖元素用逗号分隔；元素名必须逐字出现在契约清单中**。
> **跨包共享 seam**：`tools/recon_ai/evidence.py` 的 `EvidenceWriter` / `load_manifest` 是仓库级公共适配层，`attack-mcp-tool` / `attack-embeddings` / `attack-rag` / `attack-multi-agent` 均通过其 `evidence.py` 复用，物理位置刻意保留在 recon-ai 包内（避免 import 路径扩散）。职责边界见该模块 docstring；格式唯一事实源仍为 `tools/collect_evidence.py`。

| 技能 | 状态 | 消费入口 | 依赖契约元素 |
|---|---|---|---|
| attack-ai-agent | 已合入 | tools/attack_ai_agent/steps.py | --step, --cmd, --out, --strict, --shot-cmd, --screenshot, --flag, --flag-panel, --flag-shot, complete, required_status, flag_status, #### 确切命令, #### 关键输出, #### 截图（访问证明）, #### flag 取证（双通道一致）, #### 证据校验（五件套 / 三件套） |
| attack-embeddings | 已合入 | tools/attack_embeddings/evidence.py | --step, --cmd, --out, --strict, --shot-cmd, --screenshot, --flag, --flag-panel, --flag-shot, complete, required_status, flag_status, #### 确切命令, #### 关键输出, #### 截图（访问证明）, #### flag 取证（双通道一致）, #### 证据校验（五件套 / 三件套） |
| attack-infra | 已合入 | tools/attack_infra/evidence.py | --step, --cmd, --out, --strict, --shot-cmd, --screenshot, --flag, --flag-panel, --flag-shot, complete, required_status, shot_status, flag_status, #### 确切命令, #### 关键输出, #### 截图（访问证明）, #### flag 取证（双通道一致）, #### 证据校验（五件套 / 三件套） |
| attack-mcp-tool | 已合入 | tools/attack_mcp_tool/evidence.py | --step, --cmd, --out, --strict, --shot-cmd, --screenshot, --flag, --flag-panel, --flag-shot, complete, required_status, flag_status, #### 确切命令, #### 关键输出, #### 截图（访问证明）, #### flag 取证（双通道一致）, #### 证据校验（五件套 / 三件套） |
| attack-multi-agent | 已合入 | tools/attack_multi_agent/evidence.py | --step, --cmd, --out, --strict, --shot-cmd, --screenshot, --flag, --flag-panel, --flag-shot, complete, required_status, shot_status, flag_status, #### 确切命令, #### 关键输出, #### 截图（访问证明）, #### flag 取证（双通道一致）, #### 证据校验（五件套 / 三件套） |
| attack-rag | 已合入 | tools/attack_rag/evidence.py | --step, --cmd, --out, --strict, --shot-cmd, --screenshot, --flag, --flag-panel, --flag-shot, complete, required_status, flag_status, #### 确切命令, #### 关键输出, #### 截图（访问证明）, #### flag 取证（双通道一致）, #### 证据校验（五件套 / 三件套） |
| attack-supply-chain | 已合入 | tools/attack_supply_chain/evidence.py | --step, --cmd, --out, --strict, --shot-cmd, --screenshot, --flag, --flag-panel, --flag-shot, complete, required_status, flag_status, #### 确切命令, #### 关键输出, #### 截图（访问证明）, #### flag 取证（双通道一致）, #### 证据校验（五件套 / 三件套） |
| foothold-traditional | 已合入 | skills/foothold-traditional/SKILL.md | --step, --cmd, --out, --strict, --shot-cmd, --screenshot, --flag, --flag-panel, --flag-shot, complete, required_status, flag_status, #### 确切命令, #### 关键输出, #### 截图（访问证明）, #### flag 取证（双通道一致）, #### 证据校验（五件套 / 三件套） |
| loot-manage | 已合入 | tools/loot_manage/cli.py | --step, --cmd, --out, --strict, --shot-cmd, --screenshot, complete, required_status, #### 确切命令, #### 关键输出, #### 截图（访问证明）, #### 证据校验（五件套 / 三件套） |
| recon-ai | 已合入 | tools/recon_ai/evidence.py | --step, --cmd, --out, --strict, --shot-cmd, --screenshot, --flag, --flag-panel, --flag-shot, complete, required_status, flag_status, #### 确切命令, #### 关键输出, #### 截图（访问证明）, #### flag 取证（双通道一致）, #### 证据校验（五件套 / 三件套） |
| report-exam | 已合入 | tools/report_exam/index.py | #### 确切命令, #### 关键输出, #### 截图（访问证明）, #### AI 交互日志, #### flag 取证（双通道一致）, complete, required_status, shot_status, flag_status |
| threat-model | 已合入 | tools/threat_model/model.py | --step, --cmd, --out, --strict, --shot-cmd, --screenshot, --flag, --flag-panel, --flag-shot, complete, required_status, flag_status, #### 确切命令, #### 关键输出, #### 截图（访问证明）, #### flag 取证（双通道一致）, #### 证据校验（五件套 / 三件套） |
| decoy-detect | 已合入 | tools/decoy_detect/evidence.py | --step, --cmd, --out, --strict, --shot-cmd, --screenshot, --flag, --flag-panel, --flag-shot, complete, required_status, flag_status, #### 确切命令, #### 关键输出, #### 截图（访问证明）, #### flag 取证（双通道一致）, #### 证据校验（五件套 / 三件套） |
| capstone-rehearse | 已合入 | tools/capstone_rehearse/evidence.py | --step, --cmd, --out, --strict, --shot-cmd, --screenshot, --flag, --flag-panel, --flag-shot, complete, required_status, flag_status, #### 确切命令, #### 关键输出, #### 截图（访问证明）, #### flag 取证（双通道一致）, #### 证据校验（五件套 / 三件套） |
| tooling-automate | 已合入 | skills/tooling-automate/SKILL.md | --step, --cmd, --out, --strict, --shot-cmd, --screenshot, --manifest, complete, required_status, build_manifest_record, #### 确切命令, #### 关键输出, #### 截图（访问证明）, #### 证据校验（五件套 / 三件套） |
| verify-evidence | 已合入 | tools/verify_evidence.py | --step, --cmd, --out, --strict, --shot-cmd, --screenshot, --flag, --flag-panel, --flag-shot, complete, required_status, flag_status, #### 确切命令, #### 关键输出, #### 截图（访问证明）, #### flag 取证（双通道一致）, #### 证据校验（五件套 / 三件套） |
| osai-exam-readiness | 未合入 | tools/evidence_pipeline.py | --exam, --scored-target, complete, shot_status, flag_status, #### 截图（访问证明） |
