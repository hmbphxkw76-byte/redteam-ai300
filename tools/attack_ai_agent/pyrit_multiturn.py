#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""PyRIT 多轮攻击绑定（方案 P3）。

问题：`attack_multi_agent/pyrit_attack.py` 只用 `PromptSendingAttack`（单轮），
对具备对话防御的目标（如 DVAA SecureBot）无手段；而 `attack_jailbreak` 的多轮
能力（crescendo / PAIR / TAP）所需的目标形态适配此前缺失。

本模块把「目标形态」与「PyRIT 攻击类」解耦：形态由 `dialogue.ChatSpec` 决定，
攻击类由**运行时探测**决定。理由：PyRIT 1.x 内部小版本间攻击类名与构造参数
存在增删，硬编码类名会在升级后静默失效——这正是 D6/D7 那类「目标形状硬编码」
缺陷的同型风险。

不可用时一律 `executed=False` + 具体诊断，绝不把「未执行」写成「已执行」。
"""
import inspect
from dataclasses import dataclass, field
from typing import Any, Dict, List, Sequence, Tuple

# 优先尝试的多轮攻击类（按「对抗性由低到高」排序）。
# 1.2.1 实测可用项由 available_attacks() 在运行时确认，不在此断言。
CANDIDATE_ATTACKS: Tuple[str, ...] = (
    "RedTeamingAttack", "CrescendoAttack", "PairAttack", "TAPAttack",
    "PromptSendingAttack",
)


@dataclass
class MultiturnResult:
    attack_name: str = ""
    executed: bool = False
    reason: str = ""
    last_response: str = ""
    scoring: Dict[str, Any] = field(default_factory=dict)
    diagnostics: Dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> Dict[str, Any]:
        return {"attack_name": self.attack_name, "executed": self.executed,
                "reason": self.reason, "last_response": self.last_response,
                "scoring": self.scoring, "diagnostics": self.diagnostics}


def _attack_module():
    import pyrit.executor.attack as module
    return module


def _unwrap(text: str) -> str:
    """解开目标侧的 JSON 包装（如 DVAA 的 {"agent":..., "response":...}）。"""
    body = (text or "").strip()
    if not body.startswith("{"):
        return body
    try:
        import json
        obj = json.loads(body)
    except Exception:                                        # noqa: BLE001
        return body
    if isinstance(obj, dict):
        for key in ("response", "content", "text", "message"):
            value = obj.get(key)
            if isinstance(value, str) and value.strip():
                return value
    return body


def available_attacks() -> Dict[str, str]:
    """返回本环境实际可用的攻击类 -> 签名摘要。"""
    try:
        module = _attack_module()
    except Exception as exc:                                  # noqa: BLE001
        return {}
    out: Dict[str, str] = {}
    for name in CANDIDATE_ATTACKS:
        cls = getattr(module, name, None)
        if cls is None:
            continue
        try:
            out[name] = str(inspect.signature(cls.__init__))
        except (TypeError, ValueError):
            out[name] = "(签名不可读)"
    return out


def _filter_kwargs(factory, **candidates) -> Tuple[Dict[str, Any], List[str]]:
    """按签名裁剪 kwargs，返回 (可用参数, 被丢弃的键)。"""
    try:
        params = inspect.signature(factory).parameters
    except (TypeError, ValueError):
        return dict(candidates), []
    if any(p.kind is p.VAR_KEYWORD for p in params.values()):
        return dict(candidates), []
    used = {k: v for k, v in candidates.items() if k in params}
    dropped = sorted(set(candidates) - set(used))
    return used, dropped


def run_multiturn(objective: str, chat_spec, base_url: str,
                  attack_name: str = "", max_turns: int = 3,
                  timeout: int = 120, refusal_scorer_on: bool = True,
                  **subs: str) -> MultiturnResult:
    """对 `base_url + chat_spec` 施加一次多轮攻击。

    形态适配：以 ChatSpec 构造 HTTPTarget 的原始请求模板，使同一攻击类可作用
    于 `/chat {message}`、`/api/labs/{lab}/chat {prompt}` 等不同形态。

    评分配置（pyrit 1.2.1 实测签名）：
      - `AttackAdversarialConfig(target=<OPENAI_CHAT_*>)`：对抗方 LLM
      - `AttackScoringConfig(objective_scorer=..., refusal_scorer=...)`：
        原生拒绝评分器参与打分，使「目标拒绝」不会因措辞复述被判成功
    """
    result = MultiturnResult()
    try:
        import pyrit  # noqa: F401
    except ImportError as exc:
        result.reason = "pyrit 未安装：%s" % exc
        return result

    attacks = available_attacks()
    result.diagnostics["available"] = sorted(attacks)
    if not attacks:
        result.reason = "pyrit 已安装但未发现已知攻击类（executor.attack）"
        return result
    name = attack_name or next(iter(attacks))
    if name not in attacks:
        result.reason = "请求的攻击类 %s 不可用；可用项：%s" % (
            name, ", ".join(sorted(attacks)))
        return result
    result.attack_name = name

    import asyncio

    from pyrit.prompt_target import HTTPTarget

    try:
        from pyrit.executor.attack import (AttackAdversarialConfig,
                                           AttackExecutor, AttackScoringConfig)
    except ImportError as exc:
        result.reason = "攻击执行器不可用：%s" % exc
        return result

    from tools.attack_ai_agent import pyrit_semantic

    ok, diag = pyrit_semantic.availability(pyrit_semantic.ATTACK_ENV)
    result.diagnostics["attack_model"] = diag
    if not ok:
        result.reason = "缺少攻击侧模型凭据：%s" % diag
        return result

    url = chat_spec.url(base_url, **subs)
    rest = url.split("://", 1)[-1]
    host = rest.split("/", 1)[0]
    request_path = "/" + rest.split("/", 1)[1] if "/" in rest else "/"
    http_request = ("POST %s HTTP/1.1\r\nHost: %s\r\n"
                    "Content-Type: application/json\r\n\r\n%s") % (
        request_path, host, chat_spec.body_template)
    # PromptTarget 构造依赖 PyRIT 中央内存；未初始化时 pyrit 1.2.1 直接抛
    # ValueError（不是 ImportError），须在建对象前显式完成。
    result.diagnostics["memory"] = pyrit_semantic.ensure_memory()
    try:
        objective_target = HTTPTarget(http_request=http_request, use_tls=False,
                                      timeout=timeout)
    except Exception as exc:                                  # noqa: BLE001
        result.reason = "HTTPTarget 构造失败：%s: %s" % (type(exc).__name__, exc)
        return result

    try:
        adversarial = AttackAdversarialConfig(
            target=pyrit_semantic._chat_target(pyrit_semantic.ATTACK_ENV))
    except Exception as exc:                                  # noqa: BLE001
        result.reason = "对抗配置构造失败：%s: %s" % (type(exc).__name__, exc)
        return result

    objective_scorer, scorer_diag = pyrit_semantic.make_objective_scorer()
    result.diagnostics["objective_scorer"] = scorer_diag
    scoring_kwargs = {"objective_scorer": objective_scorer}
    if refusal_scorer_on:
        from pyrit.score import SelfAskRefusalScorer
        try:
            scoring_kwargs["refusal_scorer"] = SelfAskRefusalScorer(
                chat_target=pyrit_semantic._chat_target(pyrit_semantic.SCORER_ENV))
        except Exception as exc:                              # noqa: BLE001
            result.diagnostics["refusal_scorer"] = "构造失败：%s" % exc
    try:
        scoring_config = AttackScoringConfig(**scoring_kwargs)
    except Exception as exc:                                  # noqa: BLE001
        result.reason = "评分配置构造失败：%s: %s" % (type(exc).__name__, exc)
        return result

    cls = getattr(_attack_module(), name)
    kwargs, dropped = _filter_kwargs(
        cls, objective_target=objective_target,
        attack_adversarial_config=adversarial,
        attack_scoring_config=scoring_config,
        max_turns=max_turns, max_attempts=max_turns, objective=objective)
    result.diagnostics["dropped_kwargs"] = dropped
    result.diagnostics["used_kwargs"] = sorted(kwargs)
    try:
        attack = cls(**kwargs)
        executor = AttackExecutor(max_concurrency=1)
        run = asyncio.run(executor.execute_attack_async(
            attack=attack, objectives=[objective]))
    except Exception as exc:                                  # noqa: BLE001
        result.reason = "%s 执行失败：%s: %s" % (name, type(exc).__name__, exc)
        return result

    completed = getattr(run, "completed_results", None) or []
    if not completed:
        result.reason = "%s 未产生 completed_results" % name
        return result
    first = completed[0]
    last = getattr(first, "last_response", None)
    # pyrit 的 Message 对象 `get_value()` 可能返回对象 repr；优先取 original_value
    # 拿原始文本，避免把「id=UUID(...) role=assistant ...」写进证据。
    raw_text = getattr(last, "original_value", None)
    if isinstance(raw_text, str) and raw_text.strip():
        result.last_response = _unwrap(raw_text)
        result.diagnostics["raw_response"] = raw_text[:2000]
    else:
        getter = getattr(last, "get_value", None)
        result.last_response = getter() if callable(getter) else str(last or "")
    outcome = getattr(first, "outcome", None) or getattr(first, "status", None)
    scores = getattr(first, "last_score", None) or getattr(first, "score", None)
    value = getattr(scores, "get_value", None) if scores is not None else None
    result.scoring = {
        "outcome": str(outcome) if outcome is not None else "",
        "objective_score": (value() if callable(value) else None),
    }
    result.executed = True
    result.reason = "%s 执行完成（objective 数=%d）" % (name, len(completed))
    return result


__all__: Sequence[str] = ("CANDIDATE_ATTACKS", "MultiturnResult",
                          "available_attacks", "run_multiturn")
