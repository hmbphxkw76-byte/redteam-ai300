# attack-supply-chain 双轴代码审查（阶段10 code-review）

> 基线：工作树新增文件（本技能 commit 前）；diff = `tools/attack_supply_chain/`（7 模块）+ `tests/test_attack_supply_chain_seams.py`。
> 依据：spec v2 #161、工单 #173-176、CI-CD、GOVERNANCE §8.2、GLOSSARY、GLOSSARY 术语。

## 1. Standards 轴（代码写得对不对）
| # | 发现 | 位置 | 分类 |
|---|---|---|---|
| S-1 | 禁用 PyRIT 旧对象：仅 evidence.py docstring 出现「禁止」排除句，无实际使用 | `tools/attack_supply_chain/evidence.py:6` | 无违规（排除语句） |
| S-2 | 无硬编码凭据 | 全包 | 无违规 |
| S-3 | 外部重依赖惰性导入（`import art` 在方法内） | `poison_engine.py:56` | 符合 |
| S-4 | `test_emit_injected_runner` 冗余 `build_args` 调用，可精简 | `tests/test_attack_supply_chain_seams.py` | 判断项（改进） |
| S-5 | `model_scan._default_runner`（subprocess 分支）未覆盖，80.4% 边缘 | `model_scan.py` | 判断项（可接受，CI 环境才执行） |

- **Standards 硬违规：0**；判断项 2（不阻断）。

## 2. Spec 轴（做的是不是要求的）
| AC | 实现位置 | 覆盖 |
|---|---|---|
| AC-01 | `recon_input.load_assets` | 是 |
| AC-02 | 由调用方记录哈希（evidence 片段） | 契约 |
| AC-03/04 | `poison_engine`（Fake + ART 适配器） | 是（ART 真实接入=判断项） |
| AC-04 | `model_scan.scan` + `is_malicious_detected` | 是 |
| AC-05/06/07 | `injector`（pipeline/dependency/build） | 是 |
| AC-08/09/14/15 | `evidence.emit`（结构 + flag 参数） | 契约（真实执行=考试时） |
| AC-10~AC-16 | `evidence.build_args` + 证据契约测试 | 是 |
| AC-17~AC-20 | frac 校验 / art 守卫 / 未知 step 报错 | 部分（tracer bullet） |

| # | 发现 | 分类 |
|---|---|---|
| P-1 | ART 真实投毒接入为适配器桩（NotImplementedError），tracer bullet 允许 | 判断项 |
| P-2 | AC-08 下游 diff、AC-09 真实 flag 依赖考试时执行（OS-01 out of scope） | 判断项 |

- **Spec 硬违规：0**；判断项 2（沿 tracer bullet 边界，阶段9 后可续）。

## 3. 结论
- 两轴硬违规合计 **0** → 阶段10 **PASS**。
- 判断项 4 条记录为改进项（不阻断交付）。
- 门禁套件：`py_compile` OK；`unittest`（26）OK；覆盖 91.7%。
- 上游复核（§2.3）：spec/design/tickets 未被代码改动破坏（仅新增文件）。
