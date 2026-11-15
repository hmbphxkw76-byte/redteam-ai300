#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""PyRIT HTTPTarget 深度补位 seam（矩阵 §⑩：PyRIT 在多智能体场景仅做深度补位）。

B7 / ADR-0004：版本锁定 `pyrit==1.1.0`。PyRIT 在 1.1.0 无原生 MA 攻击策略，
故仅以 `HTTPTarget` 对接 A2A 端点做多轮深度利用（Crescendo/PAIR 等），
由 A2ASecBench/a2a-scanner 主导真实攻击面。

**懒导入**：本模块顶层不 import pyrit，仅在 `run_pyrit_multiturn()` 被调用时导入，
使整个包无 PyRIT 硬依赖（`py_compile` 与离线单测均不触发 pyrit 加载）。
未安装 pyrit 时显式报错，不静默失败。
"""
from typing import List, Optional

from .model import Observation


def run_pyrit_multiturn(endpoint: str, objectives: List[str],
                        scorer_substring: str = "accepted") -> Observation:
    """对可达 A2A 端点执行 PyRIT 多轮深度利用（深度补位，非主演）。

    对象图：HTTPTarget + PromptSendingAttack + SubStringScorer + SQLiteMemory（PyRIT 内核）。
    仅在 `--pyrit` 显式开启时调用；未安装 pyrit 时抛 RuntimeError（明确而非静默）。
    """
    try:
        from pyrit.executor.attack import PromptSendingAttack  # noqa
        from pyrit.prompt_target import HTTPTarget  # noqa
        from pyrit.score import SubStringScorer  # noqa
        from pyrit.memory import SQLiteMemory  # noqa
        from pyrit.common import initialize_pyrit_async  # noqa
    except ImportError as exc:  # pragma: no cover - pyrit 不为 CI 必装
        raise RuntimeError(
            "PyRIT 未安装（需 pyrit==1.1.0）；深度补位不可用。请 `pip install pyrit==1.1.0`，"
            "或在无 PyRIT 环境改用 A2ASecBench/a2a-scanner 主导路径（B9）。") from exc

    import asyncio  # pragma: no cover - 仅在真实 PyRIT 路径执行

    initialize_pyrit_async(memory_db_type="SQLite")
    memory = SQLiteMemory()
    target = HTTPTarget(http_target=endpoint, http_headers={"Content-Type": "application/json"})
    scorer = SubStringScorer(substring=scorer_substring)
    attack = PromptSendingAttack(attack_target=target, scorer=scorer, memory=memory)
    results = asyncio.run(attack.execute_attack_async(objectives=objectives))  # pragma: no cover

    joined = "\n".join(getattr(r, "text", str(r)) for r in (results or []))
    return Observation(raw=joined, text=joined, telemetry={"pyrit": "PromptSendingAttack@HTTPTarget"})
