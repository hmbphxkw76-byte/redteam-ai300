# 17 技能深度验证测试清单

生成日期：2026-11-26
适用范围：上一轮仅完成离线、假后端、清单罗列或 dry-run 验证的 17 个技能
执行原则：核心步骤必须实发请求或完成实质分析；不可达环境记 BLOCKED；产物写临时目录；不硬编码目标

## 一、AI 与网络型技能

| 编号 | 技能 | 目标环境 | 核心步骤与命令 | 通过判据 | 预期证据 |
| --- | --- | --- | --- | --- | --- |
| D-01 | attack-ai-agent | DVAR `/api/v1/chat` | `run_real.py --host/--lab` 或 `dialogue_cli.py --endpoint-template chat --target <URL>` | 真实 HTTP 200，判定非臆造，AI 交互日志落盘 | 临时目录内片段与真实响应体 |
| D-02 | attack-embeddings | 同型 embedding HTTP 端点 | `embed_invert.py --endpoint` 与 `vector_lookup.py --store` | 完成 invert 与 lookup 全流程，端点返回真实向量 | 向量与 top-k 响应 |
| D-03 | attack-jailbreak | DVAR chat | `demo.py --real --step jailbreak-02` 或 RealPyRITBackend 直调 | 真实后端可执行，不再因参数传递报错 | 步骤判定与模型响应 |
| D-04 | attack-multimodal | DVAR chat / 多模态同型端点 | `demo.py --real --step multimodal-05` | 真实后端完成多模态步骤 | 步骤判定与模型响应 |
| D-05 | attack-rag | DVAR `/api/v1/documents/search` | `cli.py --backend real --step rag-01` | 真实检索或注入通道返回可解析响应 | 检索结果与证据片段 |
| D-06 | attack-infra | kubernetes-goat `:1234` | `cli.py --target <URL> --step infra-01/03/04` | 实发 HTTP 请求并产出可核查观测 | 响应体与步骤判定 |
| D-07 | attack-supply-chain | 本地语料与目标镜像 | `ch8_steps` 全步骤 + `dataset_poison.py` | sc-09 至 sc-14 逐条执行，投毒语料可验证 | 投毒前后差分与步骤清单 |

## 二、分析与取证型技能

| 编号 | 技能 | 输入来源 | 核心步骤与命令 | 通过判据 | 预期证据 |
| --- | --- | --- | --- | --- | --- |
| D-08 | capstone-rehearse | 真实证据片段与实测耗时 | `cli --measured --closed-gates --evidence-dir` | cr-01 至 cr-06 取证链可追溯，阻断阶段如实保留 | 机读 JSON 与演练报告 |
| D-09 | decoy-detect | `tests/fixtures/decoy_scan.json` | `cli run --inventory --evidence-dir --strict-evidence` | 三维度判定与证据三件套齐全 | 判定清单与片段 |
| D-10 | foothold-ad | `tests/foothold_ad` 工件夹具 | `cli analyze --artifacts` 与 `cli verify` | 八步分析实际产出结论，工件完整性校验通过 | 分析 JSON 与校验结果 |
| D-11 | foothold-traditional | `tests/foothold_traditional` 上下文夹具 | `run_ch9` 与 `collect_evidence --step trad-09` | Ch9 入口判定与证据片段生成 | 观测文件与证据片段 |
| D-12 | loot-manage | 临时登记簿 | `register` → `query` → `set-status` → `validate` | 全链路状态一致，双通道登记可核对 | 临时登记簿与校验输出 |
| D-13 | osai-orchestrator | `--config` 与 `--anonymize` | 编排执行与匿名化 | 不只输出计划，实际能力域执行并返回结果 | 执行输出与匿名化结果 |
| D-14 | report-exam | `evidence/attack-ai-agent-real` | `index` → `build --no-package` | 主机索引与报告组装成功，证据契约不破 | 索引 JSON 与报告草稿 |
| D-15 | threat-model | `skills/threat-model/examples` 样例 | `cli --inventory --classification` | 四项质量门齐全，优先级图产出 | 模型 Markdown 与简报 |
| D-16 | tooling-automate | 七字段 tasks 清单 | 编排执行（非 dry-run） | 任务序列实际执行，退出码可核查 | 汇总 Markdown 与执行记录 |
| D-17 | verify-evidence | `loot/registry.md` 与真实报告 | `--from-loot --report --appendix` | 十项检查逐条输出，提交就绪判定正确 | 机读校验 JSON |

## 三、统一复验门禁

每完成一项，先跑定向复验，最后统一跑：

```bash
python -m unittest discover -s tests -t . -q
python scripts/measure_coverage.py --target all --min 80
python scripts/check_glossary.py
python scripts/check_token_budget.py --check
python scripts/validate_skill.py
```
