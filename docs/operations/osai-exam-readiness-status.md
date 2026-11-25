# OSAI 考试就绪状态清单（演练 · 非提交件）

> **性质**：只读状态标注，不新增权威存储。唯一事实源仍为各被指文件。
> **生成依据**：`python scripts/validate_skill_mainline.py --root .`（2026-11-25 实测）
> **纪律**：本文件不填写真实 flag、OSID、截图或考试环境事实。

## 1. 目标映射与证据

- 八计分目标映射：`docs/operations/osai-target-map.md`（8 行 / 100 分；全部标记「未就绪 / 待考试窗口填写」）。
- 只读校验：`python tools/evidence_pipeline.py --target-map docs/operations/osai-target-map.md --root .`
- 实测结果：`BLOCKED（8 项缺口）`——干净 worktree 不含 gitignore 的 `evidence/`，且正式考试事实未取得。该结果如实反映当前状态，**不是失败待掩盖项**。

## 2. 技能主线缺口

17 份既有 `SKILL.md` 已全部追加主线唯一可信源指针，校验器不再报「未引用主线」。剩余缺口为历史产物缺失：

- `tooling-automate`、`verify-evidence`：规格 v1/v2 与阶段 2–11 门禁齐全，状态 PASS。
- `capstone-rehearse`、`attack-supply-chain`：门禁链齐全，具体缺口以校验器输出为准。
- `report-exam`、`threat-model`：缺 v1/v2 与门禁记录，属高优先级（报告关与规划层）。
- 其余技能：`docs/operations/` 有设计/审查记录但未形成完整 11 阶段门禁链；本轮不伪造规格与门禁结论。

复跑命令：`python scripts/validate_skill_mainline.py --root .`（默认退出 0，只报告；`--strict` 退出 1）。

## 3. 幽灵技能（有实现无技能本体）

| 技能 | tools | tests | SKILL.md | 状态 |
|---|---|---|---|---|
| attack-jailbreak | 有 | 有 | 有 | 本轮补齐；原主线全 11 阶段 PASS（#425/#426/#432），规格与门禁记录归入规范路径 |
| attack-multimodal | 有 | 有 | 有 | 本轮补齐；原主线全 11 阶段 PASS（#433/#434/#439），规格与门禁记录归入规范路径 |
| pyrit-compat | 有 | 有 | 无 | 共享兼容工具，非技能；不要求 SKILL.md |

依据：`docs/research/osai-skill-framework-matrix.md:44-47,149-159` 与目录实测。

## 4. 影子规格

根层 24 份影子规格已归位至 `docs/specs/legacy-root/`，索引见该目录 `INDEX.md`；内容未删改，状态标「历史增量规格（非现行）」。现行规格唯一路径为 `docs/specs/<skill>-spec-{v1,v2}.md`，见 `docs/operations/osai-submission-compliance.md:70`。校验器实测根层影子规格 0 份。

## 5. 本轮改动与未改动边界

- 已落地：考试模式证据判定、八目标只读管线、考试链状态机、报告/提交预检与回填、主线校验器、17 份技能主线指针、24 份影子规格归档、两份幽灵技能本体与主线留痕、CI 独立校验步骤。
- 未落地（须在考试窗口）：真实截图、真实 flag 与双通道、OSID、报告正文、PDF/.7z、上传后 MD5。
- 未改动：`GLOSSARY.md`、官方报告模板、既有演练证据；CI 仅新增独立步骤，未改并发长行。
