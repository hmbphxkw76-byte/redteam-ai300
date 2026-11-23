#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""后端工厂：PyRIT 真实适配器与标准库假后端（唯一真实 seam）。

两个 adapter 实现同一协议 `BackendFactory`：
  - `RealPyRITBackend`：`pyrit` 只在方法体内延迟导入，装配 pyrit==1.1.0 对象图。
  - `FakePyRITBackend`：纯标准库，返回确定性响应，供 S2 测试注入（零外部依赖）。

版本锁定 pyrit==1.1.0。对象图全部取自一手源核实 M7（docs/research/
attack-jailbreak-multimodal-canonical.md），禁用 0.x 编排器名与 1.2.x 新增符号。
"""
from dataclasses import dataclass
from typing import Any, Protocol, runtime_checkable

from .steps import STEP_IDS

# 官方 v1.1.0 已核实模块路径（见 pyrit-v110-api-verification.md V2-V10）
PYRIT_ATTACK_MODULE = "pyrit.executor.attack"
PYRIT_TARGET_MODULE = "pyrit.prompt_target"
PYRIT_CONVERTER_MODULE = "pyrit.converter"
PYRIT_SCORE_MODULE = "pyrit.score"
PYRIT_MEMORY_MODULE = "pyrit.memory"
PYRIT_SETUP_MODULE = "pyrit.setup"

# 0.x 旧名在 v1.1.0 已删除；本包不引用，禁用名清单见权威索引，不在此复制字面量。


@dataclass(frozen=True)
class TargetResponse:
    """一次目标响应的可机读结果（外部行为，不含实现细节）。"""

    text: str
    verdict: str                      # 完全生效 / 部分生效 / 未生效 / 已跳过 / UNDETERMINED
    deterministic_hit: bool = False   # 确定性评分器是否命中
    llm_hit: bool = False             # LLM-as-judge 线索是否命中
    skip_reason: str = ""


@runtime_checkable
class BackendFactory(Protocol):
    """注入点协议：目标 / 评分器 / 转换器 / 记忆 / 攻击执行。"""

    def make_target(self, role: str = "objective") -> Any: ...
    def make_scorer(self, kind: str = "deterministic") -> Any: ...
    def make_converter(self, kind: str) -> Any: ...
    def make_memory(self, persistent: bool = False) -> Any: ...
    def execute(self, step_id: str, objective: str) -> TargetResponse: ...
    def describe(self) -> str: ...


class FakePyRITBackend:
    """标准库假后端：确定性响应剧本，支撑单 seam 测试（AC-15/20）。

    剧本按步骤分组：01 基线、02 单轮、03-06 多轮、07 变换、08 评分、09-10 flag。
    `responses` 可按 step_id 覆盖，`scenario` 切换有效/部分/无效三态。
    """

    def __init__(self, responses=None, scenario="effective"):
        self.responses = dict(responses or {})
        self.scenario = scenario
        self.calls: list[tuple[str, str]] = []

    def make_target(self, role="objective"):
        return {"kind": "fake_target", "role": role}

    def make_scorer(self, kind="deterministic"):
        return {"kind": "fake_scorer", "scorer_kind": kind}

    def make_converter(self, kind):
        return {"kind": "fake_converter", "converter_kind": kind}

    def make_memory(self, persistent=False):
        return {"kind": "fake_memory", "persistent": persistent}

    def execute(self, step_id, objective):
        self.calls.append((step_id, objective))
        if step_id in self.responses:
            return self.responses[step_id]
        if self.scenario == "undetermined" and step_id not in ("jailbreak-09", "jailbreak-10"):
            return TargetResponse("评分器无法确定", "UNDETERMINED")
        hit = self.scenario == "effective"
        if step_id == "jailbreak-01":
            return TargetResponse("filters/output_review/refusal 三类基线已记录", "完全生效",
                                  deterministic_hit=True)
        if step_id == "jailbreak-08":
            if self.scenario == "partial":
                return TargetResponse("部分越狱成功", "部分生效", deterministic_hit=True)
            return TargetResponse("越狱目标达成", "完全生效", deterministic_hit=hit)
        if step_id == "jailbreak-09":
            return TargetResponse("OSAI{FAKE_FLAG}", "完全生效", deterministic_hit=True)
        if step_id == "jailbreak-10":
            return TargetResponse("whoami=redteam + OSAI{FAKE_FLAG} 同屏", "完全生效",
                                  deterministic_hit=True)
        if step_id in ("jailbreak-03", "jailbreak-04", "jailbreak-05", "jailbreak-06"):
            return TargetResponse("多轮越狱响应已记录", "完全生效", deterministic_hit=hit)
        return TargetResponse("基线响应已记录", "完全生效", deterministic_hit=hit)

    def describe(self):
        return "FakePyRITBackend(scenario=%s, calls=%d)" % (self.scenario, len(self.calls))


class RealPyRITBackend:
    """真实 seam：延迟导入 pyrit==1.1.0，装配已核实的攻击对象图。

    仅在方法体内 import pyrit，未安装时 ImportError 由调用方处理（CI 用假后端）。
    """

    def __init__(self, chat_endpoint=None, api_key=None, memory_db_type="SQLite"):
        self.chat_endpoint = chat_endpoint
        self.api_key = api_key
        self.memory_db_type = memory_db_type

    def _attack_mod(self):
        import importlib
        return importlib.import_module(PYRIT_ATTACK_MODULE)

    def make_target(self, role="objective"):
        import importlib
        target_mod = importlib.import_module(PYRIT_TARGET_MODULE)
        return target_mod.OpenAIChatTarget(
            endpoint=self.chat_endpoint, api_key=self.api_key)

    def make_scorer(self, kind="deterministic"):
        import importlib
        score_mod = importlib.import_module(PYRIT_SCORE_MODULE)
        if kind == "deterministic":
            return score_mod.SubStringScorer()
        return score_mod.SelfAskRefusalScorer(chat_target=self.make_target("scorer"))

    def make_converter(self, kind):
        import importlib
        conv_mod = importlib.import_module(PYRIT_CONVERTER_MODULE)
        mapping = {
            "base64": "Base64Converter",
            "rot13": "ROT13Converter",
            "leetspeak": "LeetspeakConverter",
            "translation": "TranslationConverter",
        }
        cls = getattr(conv_mod, mapping[kind])
        return cls()

    def make_memory(self, persistent=False):
        import importlib
        setup_mod = importlib.import_module(PYRIT_SETUP_MODULE)
        db_type = self.memory_db_type if persistent else "InMemory"
        return setup_mod.initialize_pyrit_async(memory_db_type=db_type)

    def execute(self, step_id, objective):
        attack_mod = self._attack_mod()
        strategies = {
            "jailbreak-02": "PromptSendingAttack",
            "jailbreak-03": "CrescendoAttack",
            "jailbreak-04": "PAIRAttack",
            "jailbreak-05": "TreeOfAttacksWithPruningAttack",
            "jailbreak-06": "RedTeamingAttack",
        }
        strategy = strategies.get(step_id, "PromptSendingAttack")
        executor = attack_mod.AttackExecutor(max_concurrency=1)
        attack = getattr(attack_mod, strategy)(objective_target=self.make_target())
        result = executor.execute_attack_async(attack=attack, objectives=[objective])
        response_text = (str(result.last_response)
                         if hasattr(result, "last_response") else str(result))
        # 真正调用评分器，不以其对象真值伪造命中（C8 证据真实性）。
        scorer = self.make_scorer("deterministic")
        if not (scorer and response_text):
            return TargetResponse(text=response_text, verdict="UNDETERMINED")
        try:
            hit = bool(scorer.score(text=response_text, objective=objective))
        except (TypeError, AttributeError):
            # 评分器签名在核实闸 Q1 未定；无法评分时如实标 UNDETERMINED，不臆断成功。
            return TargetResponse(text=response_text, verdict="UNDETERMINED")
        return TargetResponse(
            text=response_text,
            verdict="完全生效" if hit else "UNDETERMINED",
            deterministic_hit=hit,
        )

    def describe(self):
        return "RealPyRITBackend(pyrit==1.1.0, endpoint=%s)" % (self.chat_endpoint or "<unset>")


def get_backend(real=False, **kwargs):
    """工厂入口：默认假后端（零依赖）；real=True 装配真实 seam。"""
    if real:
        return RealPyRITBackend(**kwargs)
    return FakePyRITBackend(**kwargs)
