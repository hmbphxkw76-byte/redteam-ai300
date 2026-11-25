# OSAI 考试就绪状态清单（演练 · 非提交件）

> **性质**：只读状态标注，不新增权威存储。唯一事实源仍为各被指文件。
> **生成依据**：`python scripts/validate_skill_mainline.py --root .`（2026-11-25 实测）
> **纪律**：本文件不填写真实 flag、OSID、截图或考试环境事实。

## 1. 目标映射与证据

- 八计分目标映射：`docs/operations/osai-target-map.md`（8 行 / 100 分；全部标记「未就绪 / 待考试窗口填写」）。
- 只读校验：`python tools/evidence_pipeline.py --target-map docs/operations/osai-target-map.md --root .`
- 实测结果：`BLOCKED（8 项缺口）`——干净 worktree 不含 gitignore 的 `evidence/`，且正式考试事实未取得。该结果如实反映当前状态，**不是失败待掩盖项**。

## 2. 技能主线缺口

实测 17 份 `SKILL.md` 全部缺主线唯一可信源指针（判据 `skill-mainline-workflow`）。其中：

- `tooling-automate`、`verify-evidence`：规格 v1/v2 与阶段 2–11 门禁齐全，仅缺指针。
- `capstone-rehearse`、`attack-supply-chain`：门禁链齐全，具体缺口以校验器输出为准。
- `report-exam`、`threat-model`：缺 v1/v2 与门禁记录，属高优先级（报告关与规划层）。
- 其余技能：`docs/operations/` 有设计/审查记录但未形成完整 11 阶段门禁链。

复跑命令：`python scripts/validate_skill_mainline.py --root .`（默认退出 0，只报告；`--strict` 退出 1）。

## 3. 幽灵技能（有实现无技能本体）

| 技能 | tools | tests | SKILL.md | 状态 |
|---|---|---|---|---|
| attack-jailbreak | 有 | 有 | 无 | 待补主线阶段 1–11；矩阵第 17 项已登记 |
| attack-multimodal | 有 | 有 | 无 | 待补主线阶段 1–11；矩阵第 18 项已登记 |
| pyrit-compat | 有 | 有 | 无 | 共享兼容工具，非技能；不要求 SKILL.md |

依据：`docs/research/osai-skill-framework-matrix.md:44-47,149-159` 与目录实测。

## 4. 影子规格

根层 `spec-v1-*.md` / `spec-v2-*.md` / `spec-design-*.md` 共 **24 份**，不在 `docs/specs/` 规范路径内，且未被 `docs/` 正文引用。状态：**影子规格，待迁移或归档**；不得当作现行规格使用。规范路径见 `docs/operations/osai-submission-compliance.md:70`。

## 5. 本轮改动与未改动边界

- 已落地：考试模式证据判定、八目标只读管线、考试链状态机、报告/提交预检、主线校验器。
- 未落地（须在考试窗口）：真实截图、真实 flag 与双通道、OSID、报告正文、PDF/.7z、上传后 MD5。
- 未改动：17 份 `SKILL.md` 正文、`GLOSSARY.md`、CI 工作流、官方报告模板、既有演练证据。
