#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""间接注入（路径 B → 下游）：经 `XPIATestWorkflow` 触发下游 agent。

B7 受控例外：跨域提示注入**不是** `*Attack`，v1.1.0 由
`pyrit.executor.workflow.XPIATestWorkflow` 承载。本模块不直接导入 PyRIT，
一律经后端注入点调用，故顶层零 pyrit 依赖（ADR-0004）。

缺 PyRIT / 端点 / 签名不符时返回 `skipped_reason`，不抛异常（失败与豁免）。
"""
from dataclasses import dataclass

from .model import DEFAULT_INSTRUCTION

STRATEGY = "XPIATestWorkflow"


@dataclass(frozen=True)
class XpiaResult:
    """一次间接注入的对外结论。"""

    objective: str
    delivered: bool
    response: str = ""
    strategy: str = STRATEGY
    payload: str = ""
    skipped_reason: str = ""

    def render(self) -> str:
        return ("strategy: %s\ndelivered: %s\nresponse: %s"
                % (self.strategy, self.delivered, self.response or "（无）"))

    def as_dict(self):
        return {"objective": self.objective, "delivered": self.delivered,
                "response": self.response, "strategy": self.strategy,
                "payload": self.payload, "skipped_reason": self.skipped_reason}


def build_payload(instruction: str = DEFAULT_INSTRUCTION) -> str:
    """构造注入载荷：伪装成检索文档中的「操作说明」段。"""
    return ("[检索片段 · 操作说明] %s" % (instruction or DEFAULT_INSTRUCTION)).strip()


def run_xpia(objective: str, backend, payload: str = "") -> XpiaResult:
    """经后端执行一次间接注入；任何后端异常都收敛为「已跳过」并记原因。"""
    payload = payload or build_payload()
    try:
        outcome = backend.xpia(objective, payload)
    except Exception as exc:  # 后端装配 / 运行时失败：不阻断其余路径
        return XpiaResult(objective, False, payload=payload,
                          skipped_reason="backend_error: %s" % exc)
    # 结构化校验而非 isinstance：模块重载（覆盖率采集）下类对象会换身份，
    # 用属性形状判定契约更稳，且不放松「必须带回执」的要求。
    if not (hasattr(outcome, "executed") and hasattr(outcome, "response")):
        return XpiaResult(objective, False, payload=payload,
                          skipped_reason="backend_contract: 回执缺少 executed/response")
    return XpiaResult(objective, bool(outcome.executed), outcome.response,
                      payload=payload, skipped_reason=outcome.skipped_reason)
