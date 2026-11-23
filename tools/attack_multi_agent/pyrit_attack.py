#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""PyRIT HTTPTarget 深度补位 seam（矩阵 §⑩：PyRIT 在多智能体场景仅做深度补位）。

版本基线 1.1.0；目标版本 1.2.1（单一来源 tools/pyrit_compat）。
PyRIT 无原生 MA 攻击策略，故仅以 HTTPTarget 对接 A2A 端点做多轮深度利用，
由 A2ASecBench/a2a-scanner 主导真实攻击面。

**懒导入**：本模块顶层不 import pyrit，仅在 run_pyrit_multiturn() 被调用时导入，
使整个包无 PyRIT 硬依赖（py_compile 与离线单测均不触发 pyrit 加载）。
未安装 pyrit 或版本不匹配时显式报错，不静默失败。
"""
import importlib
from typing import List
from urllib.parse import urlparse

from tools.pyrit_compat import TARGET_VERSION
from tools.pyrit_compat.compat import adapt_kwargs, require_runtime_version, resolve_import

from .model import Observation


def run_pyrit_multiturn(endpoint: str, objectives: List[str],
                        scorer_substring: str = "accepted") -> Observation:
    """对可达 A2A 端点执行 PyRIT 多轮深度利用（深度补位，非主演）。

    对象图（1.2.1 一手源核实）：HTTPTarget(http_request=...) +
    PromptSendingAttack(objective_target=...) + AttackExecutor.execute_attack_async()
    + SubStringScorer。1.1.0 遗留调用形态由兼容层显式拒绝。
    """
    require_runtime_version(TARGET_VERSION, allow_offline_stub=True)
    try:
        module, name = resolve_import("pyrit.setup", "initialize_pyrit_async", TARGET_VERSION)
        initialize_pyrit_async = getattr(importlib.import_module(module), name)
        from pyrit.executor.attack import AttackExecutor, PromptSendingAttack
        from pyrit.prompt_target import HTTPTarget
        from pyrit.score import ContentScorable, SubStringScorer
    except ImportError as exc:  # pragma: no cover - pyrit 不为 CI 必装
        raise RuntimeError(
            "PyRIT 未安装（需 pyrit==%s）；深度补位不可用。"
            "请按 docs/operations/pyrit-upgrade-runbook.md 安装（版本事实："
            "tools/pyrit_compat/data/versions/%s.json），或在无 PyRIT 环境改用 "
            "A2ASecBench/a2a-scanner 主导路径（B9）。" % (TARGET_VERSION, TARGET_VERSION)
        ) from exc

    import asyncio  # pragma: no cover - 仅在真实 PyRIT 路径执行

    parsed = urlparse(endpoint)
    http_request = (
        "POST %s HTTP/1.1\r\nHost: %s\r\nContent-Type: application/json\r\n\r\n{PROMPT}"
    ) % (parsed.path or "/", parsed.netloc)
    target_kwargs, _ = adapt_kwargs(
        "pyrit.prompt_target.HTTPTarget",
        {"http_request": http_request, "prompt_regex_string": "{PROMPT}"}, TARGET_VERSION)

    asyncio.run(initialize_pyrit_async(memory_db_type="SQLite"))
    target = HTTPTarget(**target_kwargs)
    attack_kwargs, _ = adapt_kwargs(
        "pyrit.executor.attack.PromptSendingAttack",
        {"objective_target": target}, TARGET_VERSION)
    attack = PromptSendingAttack(**attack_kwargs)
    executor = AttackExecutor(max_concurrency=1)
    result = asyncio.run(executor.execute_attack_async(  # pragma: no cover
        attack=attack, objectives=objectives))
    completed = getattr(result, "completed_results", None) or []
    joined = "\n".join(
        getattr(item, "text", None)
        or (item.last_response.get_value() if hasattr(item, "last_response")
            and hasattr(item.last_response, "get_value") else str(item))
        for item in completed)

    scorer = SubStringScorer(substring=scorer_substring)
    scores = asyncio.run(scorer.score_async(
        scorable=ContentScorable(value=joined, data_type="text"),
        objective=objectives[0] if objectives else ""))
    hit = any(str(s.score_value).lower() == "true" for s in scores)
    return Observation(raw=joined, text=joined, telemetry={
        "pyrit": "PromptSendingAttack@HTTPTarget",
        "target_version": TARGET_VERSION,
        "deterministic_hit": hit,
    })
