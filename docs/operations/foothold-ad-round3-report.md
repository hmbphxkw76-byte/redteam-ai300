# foothold-ad 第三轮报告：影子端点、主线留痕与 PR 合入

> 承接 `foothold-ad-verification.md`（第一、二轮）。本轮目标：无真实环境下可完成项全部收敛。
> 执行顺序：A（影子端点）→ C（主线留痕）→ B（PR）。

## 1. 结论摘要

| 项 | 结果 | 判定 |
|---|---|---|
| A recon-ai 影子端点（方案 A） | `tools/recon_ai/shadow.py` + recon-05/`ch2` 接入 + 13 例测试 | PASS |
| C 主线留痕 GAP | spec v1/v2 + 10 份门禁记录；`validate_skill_mainline --strict` → `foothold-ad PASS` | PASS |
| B PR 合入记录 | PR #452 → merge `9166e8b`；CI 全绿 | PASS |
| 遗留 | 阶段 4/5/10 记 `PARTIAL`；真实域联调未做 | 已声明 |

## 2. A — 影子端点（方案 A）

**做法**：OpenAPI `paths` 与前端 HTML/JS 路径字面量做差集，输出未声明但被引用的候选端点。

| 能力 | 实现 |
|---|---|
| 路径归一 | 去查询串/锚点/尾斜杠、折叠重复斜杠、数字与 GUID 归一为 `{id}` |
| 噪声过滤 | 静态资源后缀、跨域与协议相对 URL |
| 置信度 | 具体段 ≥2 记 high；仅 1 段记 medium（易与通用路由重名） |
| 确定性 | 按路径排序；同输入同输出 |
| 集成 | `recon-05`「关键输出」+ `ch2.analyze` 的 `kind=shadow`；不新增 step_id、不改七字段 |

**验证**：`tests/recon_ai` 171 例通过；`shadow.py` 覆盖率 98.8%，recon-ai 合计 85.2%（门槛 80%）。端到端样例（1 条声明 + 3 条引用）产出 2 条 high 候选，`validate_analysis` 零违规。

**边界**：命中仅表示「前端引用了未声明路径」，不等于端点可用；可用性仍由 recon 探测判定。

## 3. C — 主线留痕

| 产物 | 实测 |
|---|---|
| `docs/specs/foothold-ad-spec-v1.md` | 4025/8000 字节，七节齐备 |
| `docs/specs/foothold-ad-spec-v2.md` | 5171/10000 字节，AC-01..AC-15 布尔化 |
| `docs/operations/foothold-ad-gate-stage2..11.md` | 10 份，832–946 字节（上限 2000） |
| `validate_skill_mainline.py --strict` | `foothold-ad PASS`（总计仍 BLOCKED，系其他技能历史 GAP） |

**如实标注的偏差**（写入对应门禁记录，未粉饰）：

1. 规格与门禁为**实现后回溯补录**，阶段顺序倒置（stage2/stage3 记录）。
2. 阶段 4 `to-tickets` 与 5 `triage` 无 issue，记 `PARTIAL`，不补造工单。
3. 阶段 10 `code-review` 无独立 reviewer，以自查 + 门禁替代，记 `PARTIAL`。
4. 阶段 1 `research` 仅完成课程文档源；外部权威源已核实（ATT&CK / SpecterOps），商业工具文档未覆盖。

## 4. B — PR 合入

首轮为直接合并（`f32480c`），GitHub 无法对已合并分支开非空 PR。处置：

1. 从 `feat/foothold-ad` 建 `feat/foothold-ad-v2`，提交 `b68198c`（19 文件 / +556 行）。
2. PR **#452**，正文 1770/3000 字节，首段声明「首轮已直接合并，本 PR 为追溯记录 + 增量」。
3. 检查全绿后 `--merge` 合入，merge commit **`9166e8b`**。

CI：静态检查 S1、自动化测试 S2、AC-12 真实 PDF 冒烟均 pass。

## 5. 偏差与未做

| 项 | 状态 | 说明 |
|---|---|---|
| 独立代码评审 | 未做 | 单人会话无法满足；PR 正文列待评审点 |
| 真实域联调 | 未做 | 无 AD 靶场；全部结论限定为「夹具验证」 |
| `recon-ai/SKILL.md` 余量 | 2 字节 | 13998/14000，后续改动须先腾位 |
| 本报告提交方式 | 直接提交 | docs-only 更新；已由 S1 静态门禁覆盖 |

## 6. 复现命令

```bash
python -m unittest tests.recon_ai.test_recon_ai_shadow
python scripts/measure_coverage.py --target recon-ai --min 80
python scripts/validate_skill_mainline.py --root . --strict
python scripts/check_token_budget.py --artifact spec-v1 docs/specs/foothold-ad-spec-v1.md
python scripts/check_token_budget.py --artifact spec-v2 docs/specs/foothold-ad-spec-v2.md
python scripts/check_token_budget.py --artifact pr-body /tmp/pr_body.md
```

## 7. 变更文件

| 类型 | 路径 |
|---|---|
| 新增 | `tools/recon_ai/shadow.py`、`tests/recon_ai/test_recon_ai_shadow.py` |
| 新增 | `docs/specs/foothold-ad-spec-v1.md`、`-v2.md` |
| 新增 | `docs/operations/foothold-ad-gate-stage2..11.md`（10 份） |
| 新增 | `docs/operations/foothold-ad-round3-report.md`（本文件） |
| 修改 | `tools/recon_ai/ch2.py`（`kind=shadow` 分支 + `parse_shadow_endpoints`） |
| 修改 | `skills/recon-ai/SKILL.md`（recon-05 影子端点一行） |
| 修改 | `scripts/tools_manifest.json`（recon-ai 增 shadow 模块与测试） |
| 修改 | `docs/operations/foothold-ad-design.md`（§8 状态） |
| 修改 | `docs/research/ai300-lab-scenario-coverage.md`（P0 改判已实施，30/13/7） |
| 修改 | `docs/operations/foothold-ad-verification.md`（指向本报告） |
