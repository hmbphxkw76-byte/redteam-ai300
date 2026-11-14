#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""attack-ai-agent 三条攻击路径的对象图规格（纯数据，顶层不导入 pyrit）。

设计依据：issue #83「设计记录 (codebase-design)」方案 A 与「一手源勘误 (F3)」。
对象图以 ComponentSpec 声明「攻击策略 / 目标 / 转换器 / 评分器 / 记忆」五类构件，
由 backends.BackendFactory 负责实例化。规格与实例化分离是单缝的前提：测试可注入
标准库假后端，在**未安装 pyrit** 的环境验证全部外部行为（AC-23 / AC-25）。

类名依据（一手源，2026-11-14 核实）：
  docs/research/pyrit-v110-api-verification.md  V1-V14 / X1-X4
  docs/research/pyrit-canonical-references.md  §3 / §4
版本锁 pyrit==1.1.0（ADR-0004）；禁止 0.x 命名空间。
"""

from dataclasses import dataclass, field
from typing import Any, Dict, Tuple


@dataclass(frozen=True)
class ComponentSpec:
    """对象图中一个构件的声明（规格，不是实例）。"""

    role: str                                  # 攻击策略 / 目标 / 转换器 / 评分器 / 记忆
    api_name: str                              # PyRIT v1.1.0 官方类名
    module: str                                # PyRIT v1.1.0 官方模块路径
    params: Dict[str, Any] = field(default_factory=dict)
    note: str = ""


@dataclass(frozen=True)
class PathSpec:
    """一条攻击路径的完整对象图规格。"""

    path_id: str
    owasp: str
    components: Tuple[ComponentSpec, ...]
    steps: Tuple[str, ...]
    b7_exception: bool = False
    b7_reason: str = ""


# 稳定步骤标识（GOVERNANCE §6；S2 证据契约夹具的机器判据，非易变实现细节）
ALL_STEPS: Tuple[str, ...] = tuple("aia-%02d" % i for i in range(1, 13))

B7_EXCEPTION_REASON = (
    "间接注入在 PyRIT v1.1.0 由 pyrit.executor.workflow 的工作流策略表达，"
    "不属于 pyrit.executor.attack 下的 *Attack；依据 V11 / V12 / X1 登记为 B7 受控例外，"
    "不引入任何 0.x 禁用名称，不改变其余路径的策略归属。"
)


def build_path_a() -> PathSpec:
    """路径 A — 提示注入（OWASP ASI01）：直接注入 + 间接注入（XPIA）。"""
    return PathSpec(
        path_id="A",
        owasp="ASI01",
        steps=("aia-02", "aia-03", "aia-04"),
        b7_exception=True,
        b7_reason=B7_EXCEPTION_REASON,
        components=(
            ComponentSpec("攻击策略", "PromptSendingAttack", "pyrit.executor.attack",
                          {"drive": "单轮 objective，覆盖系统提示"}),
            ComponentSpec("攻击策略", "XPIATestWorkflow", "pyrit.executor.workflow",
                          {"drive": "把隐藏指令嵌入 agent 会摄取的文档/邮件/网页/DB 字段"},
                          "B7 受控例外：间接注入仅能由工作流策略表达（见 b7_reason）"),
            ComponentSpec("执行器", "AttackExecutor", "pyrit.executor.attack",
                          {"method": "execute_attack_async", "max_concurrency": 1}),
            ComponentSpec("目标", "OpenAIChatTarget", "pyrit.prompt_target",
                          {"purpose": "agent Web / API 入口"}),
            ComponentSpec("转换器", "AttackConverterConfig", "pyrit.executor.attack",
                          {"field": "request_converters"}),
            ComponentSpec("转换器", "ConverterConfiguration", "pyrit.prompt_normalizer",
                          {"factory": "from_converters"}),
            ComponentSpec("转换器", "Base64Converter", "pyrit.converter",
                          {"chain": "绕过输入过滤"}),
            ComponentSpec("转换器", "TranslationConverter", "pyrit.converter"),
            ComponentSpec("转换器", "ROT13Converter", "pyrit.converter"),
            ComponentSpec("转换器", "LeetspeakConverter", "pyrit.converter"),
            ComponentSpec("评分器", "SelfAskTrueFalseScorer", "pyrit.score",
                          {"use": "机读线索"}),
            ComponentSpec("评分器", "TrueFalseQuestion", "pyrit.score",
                          {"use": "true_description 描述泄露系统提示 / 执行被劫持动作"}),
            ComponentSpec("评分器", "SubStringScorer", "pyrit.score",
                          {"use": "决定性证据：内部指令 / 工具名"}),
            ComponentSpec("配置", "AttackScoringConfig", "pyrit.executor.attack",
                          {"field": "objective_scorer"}),
            ComponentSpec("记忆", "initialize_pyrit_async", "pyrit.setup",
                          {"memory_db_type": "InMemory"},
                          "路径 A 无需跨会话；路径 B 必须改文件型持久后端"),
        ),
    )


def build_path_b() -> PathSpec:
    """路径 B — 记忆系统滥用（OWASP ASI06）：投毒 + 跨会话召回泄露。"""
    return PathSpec(
        path_id="B",
        owasp="ASI06",
        steps=("aia-05", "aia-06", "aia-07"),
        components=(
            ComponentSpec("攻击策略", "RedTeamingAttack", "pyrit.executor.attack",
                          {"max_turns": 5, "drive": "建立上下文并写入伪造事实"}),
            ComponentSpec("攻击策略", "PromptSendingAttack", "pyrit.executor.attack",
                          {"drive": "新会话查询召回，判定是否泄露凭据/历史/内部指令"}),
            ComponentSpec("执行器", "AttackExecutor", "pyrit.executor.attack",
                          {"method": "execute_attack_async"}),
            ComponentSpec("目标", "OpenAIChatTarget", "pyrit.prompt_target",
                          {"purpose": "被测 agent 与攻击方 LLM"}),
            ComponentSpec("配置", "AttackAdversarialConfig", "pyrit.executor.attack",
                          {"field": "攻击方 LLM"}),
            ComponentSpec("配置", "RTASystemPromptPaths", "pyrit.executor.attack"),
            ComponentSpec("转换器", "AttackConverterConfig", "pyrit.executor.attack",
                          {"drive": "写入伪造事实时绕过输入过滤"}),
            ComponentSpec("评分器", "SelfAskTrueFalseScorer", "pyrit.score"),
            ComponentSpec("评分器", "SubStringScorer", "pyrit.score",
                          {"use": "决定性证据：召回的伪造事实 / 凭据片段"}),
            ComponentSpec("记忆", "SQLiteMemory", "pyrit.memory",
                          {"persistent": True, "db_path": "<由 target_config 注入>"},
                          "文件型持久后端；跨会话验证的必要条件"),
            ComponentSpec("记忆", "initialize_pyrit_async", "pyrit.setup",
                          {"memory_db_type": "SQLite"},
                          "memory_db_type 取字符串字面量（V8）；不可使用内存型后端"),
            ComponentSpec("取证", "PrettyAttackResultMemoryPrinter",
                          "pyrit.output.attack_result.pretty",
                          {"method": "write_async", "memory_labels": {"harm_category": "memory_poison"}},
                          "对话导出采用 V13 已核实的打印机（一手源核实 X2 已排除旧名）"),
        ),
    )


def build_path_c() -> PathSpec:
    """路径 C — 工具集成滥用（OWASP ASI02）：越权调用与外泄取证。"""
    return PathSpec(
        path_id="C",
        owasp="ASI02",
        steps=("aia-08", "aia-09", "aia-10"),
        components=(
            ComponentSpec("攻击策略", "RedTeamingAttack", "pyrit.executor.attack",
                          {"drive": "诱导以合法工具执行非预期动作"}),
            ComponentSpec("攻击策略", "PromptSendingAttack", "pyrit.executor.attack",
                          {"drive": "指向工具面端点的单轮诱导"}),
            ComponentSpec("执行器", "AttackExecutor", "pyrit.executor.attack",
                          {"method": "execute_attack_async"}),
            ComponentSpec("目标", "HTTPTarget", "pyrit.prompt_target",
                          {"purpose": "对接 MCP / 工具面端点",
                           "callback": "get_http_target_json_response_callback_function"},
                          "PyRIT v1.1.0 核心无 MCP 专用攻击策略（V14）；与 D7 attack-mcp-tool 衔接点，本规格不实现 D7"),
            ComponentSpec("目标", "get_http_target_json_response_callback_function",
                          "pyrit.prompt_target"),
            ComponentSpec("转换器", "AttackConverterConfig", "pyrit.executor.attack"),
            ComponentSpec("评分器", "SubStringScorer", "pyrit.score",
                          {"use": "决定性证据：外呼 URL / 越权文件内容"}),
            ComponentSpec("评分器", "SelfAskTrueFalseScorer", "pyrit.score",
                          {"use": "判定越权动作是否发生"}),
        ),
    )


def build_all_paths() -> Tuple[PathSpec, ...]:
    """返回三条路径的对象图规格（顺序与 SKILL.md 执行体一致）。"""
    return (build_path_a(), build_path_b(), build_path_c())
