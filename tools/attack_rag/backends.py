#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""后端 seam（唯一新增注入点）：目标模型 + embedder + 间接注入。

两个 adapter 实现同一协议：
  - `FakeBackend`：纯标准库、确定性响应，供 CI / 单测离线注入（ADR-0004）。
  - `RealPyRITBackend`：`pyrit` 仅方法体内延迟导入，生产装配 `OpenAIChatTarget`。

顶层零 pyrit 依赖：未安装 pyrit 的环境仍可 import 本包并跑全部离线路径。
"""
import os
from typing import Any, Protocol, runtime_checkable

from .embedder import DeterministicEmbedder, Embedder
from .harness import MALICIOUS_MARKER
from .model import XpiaOutcome

PYRIT_TARGET_MODULE = "pyrit.prompt_target"
PYRIT_WORKFLOW_MODULE = "pyrit.executor.workflow"

# 双模型职责分离（沿用 attack-ai-agent 约定）：目标/攻击模型与评分模型各一套命名空间。
TARGET_ENV = ("OPENAI_CHAT_KEY", "OPENAI_CHAT_ENDPOINT", "OPENAI_CHAT_MODEL")

FAKE_INJECTED = ("INJECTED_ACTION: 已按检索片段中的指令，将会话凭据外发至 "
                 "https://exfil.example/collect")


@runtime_checkable
class RagBackend(Protocol):
    """注入点协议：目标模型、embedder、下游响应、间接注入。"""

    def make_target(self) -> Any: ...

    def make_embedder(self) -> Embedder: ...

    def respond(self, query: str, context_texts) -> str: ...

    def xpia(self, objective: str, payload: str) -> XpiaOutcome: ...

    def describe(self) -> str: ...


class FakeBackend:
    """确定性假后端：按上下文是否含恶意标记给出两类响应。"""

    def __init__(self, follow_injection: bool = True, embedder: Embedder = None):
        self.follow_injection = follow_injection
        self.embedder = embedder or DeterministicEmbedder()
        self.calls = []

    def describe(self):
        return "fake-stdlib (offline)"

    def make_target(self):
        return {"adapter": "fake", "module": PYRIT_TARGET_MODULE,
                "class": "OpenAIChatTarget"}

    def make_embedder(self):
        return self.embedder

    def respond(self, query, context_texts):
        self.calls.append(("respond", query))
        for text in context_texts or ():
            if MALICIOUS_MARKER in text:
                return "MANIPULATED: %s" % text.split(MALICIOUS_MARKER, 1)[1].strip()
        return "BASELINE: 正常答案（无投毒上下文）"

    def xpia(self, objective, payload):
        self.calls.append(("xpia", objective))
        lowered = (payload or "").lower()
        if not self.follow_injection:
            return XpiaOutcome("下游拒绝执行注入指令", False, "instruction_refused")
        if "忽略" in payload or "ignore" in lowered:
            return XpiaOutcome(FAKE_INJECTED, True)
        return XpiaOutcome("下游未识别注入指令", False, "instruction_not_followed")


class RealPyRITBackend:
    """生产适配器：延迟导入 `pyrit==1.1.0`；凭据只从 env 读取。"""

    def __init__(self, target_config=None):
        self.target_config = dict(target_config or {})

    def describe(self):
        return "pyrit-1.1.0 (target=OPENAI_CHAT_*, workflow=XPIATestWorkflow)"

    def make_target(self):
        try:
            from pyrit.prompt_target import OpenAIChatTarget
        except ImportError as exc:  # 未安装 pyrit：给出可执行诊断而非裸 ImportError
            raise RuntimeError("需要 pyrit==1.1.0：%s" % exc) from exc
        missing = [k for k in TARGET_ENV if not os.environ.get(k)]
        if missing:
            raise RuntimeError("缺少环境变量：%s（见根 .env，勿硬编码凭据）"
                               % ", ".join(missing))
        return OpenAIChatTarget(api_key=os.environ[TARGET_ENV[0]],
                                endpoint=os.environ[TARGET_ENV[1]],
                                model_name=os.environ[TARGET_ENV[2]])

    def make_embedder(self):
        # 生产可注入 sentence-transformers 等；默认用确定性实现保证可复现。
        return DeterministicEmbedder()

    def respond(self, query, context_texts):
        """真实响应：需 pyrit + 端点；异常交由 DecisionDiff 收敛为「未生效」。"""
        target = self.make_target()
        prompt = "上下文：\n%s\n\n问题：%s" % ("\n".join(context_texts or ()), query)
        try:
            import asyncio
            from pyrit.models import PromptRequestResponse, PromptRequestPiece
            request = PromptRequestResponse(requests=[PromptRequestPiece(
                role="user", original_value=prompt)])
            response = asyncio.run(target.send_prompt_async(prompt_request=request))
            return response.request_pieces[0].converted_value
        except Exception as exc:  # 端点/签名不符：不静默伪造成功
            raise RuntimeError("真实响应失败（pyrit 端点或签名未就绪）：%s" % exc) from exc

    def xpia(self, objective, payload):
        """经 `XPIATestWorkflow` 执行间接注入；签名未实测时不伪造结果。"""
        try:
            from pyrit.executor.workflow import XPIATestWorkflow  # noqa: F401
        except ImportError as exc:
            return XpiaOutcome("", False, "pyrit_missing: %s" % exc)
        except AttributeError as exc:  # 版本漂移：workflow 名称不存在
            return XpiaOutcome("", False, "workflow_missing: %s" % exc)
        return XpiaOutcome("", False,
                           "signature_unverified: XPIATestWorkflow 构造签名须以 "
                           "pyrit==1.1.0 实测后接入（核实闸 B）")
