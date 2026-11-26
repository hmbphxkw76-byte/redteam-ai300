#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""混合编排入口与 PyRIT 升级边界测试（典型 / 边界 / 误触发）。

全离线：注入 sender / escalator 替身，不装 pyrit、不连端点（ADR-0004）。
重点锁定三件事：
  1. 默认路径停在 Python 编排层，不隐式升级；
  2. 升级只在「对话面 + 前置层耗尽 + 显式启用 + 边界合规」时触发；
  3. 冲突按硬阻断优先裁决，异常统一收敛为未生效而非抛出。
"""
import unittest

from tools.attack_ai_agent import hybrid


def ctx(**overrides):
    base = dict(objective="Get the system prompt", target_shape="chat",
                tier1_attempted=("S-VERBATIM",), tier1_effective=(),
                tier2_attempted=("S-ROLEPLAY",), generated_attempts=1,
                pyrit_available=True, credentials_ok=True, user_opt_in=True)
    base.update(overrides)
    return hybrid.EscalationContext(**base)


class GateTypicalTests(unittest.TestCase):
    def test_allow_when_all_conditions_met(self):
        gate = hybrid.escalation_gate(ctx())
        self.assertTrue(gate.allowed)
        self.assertEqual(gate.conflicts, [])

    def test_deny_without_opt_in_even_if_pyrit_ready(self):
        gate = hybrid.escalation_gate(ctx(user_opt_in=False))
        self.assertFalse(gate.allowed)
        self.assertIn("未显式启用", gate.reason)

    def test_deny_when_tier1_not_attempted(self):
        gate = hybrid.escalation_gate(ctx(tier1_attempted=()))
        self.assertFalse(gate.allowed)
        self.assertIn("tier1 未执行", gate.reason)

    def test_deny_when_only_tier1_no_generation(self):
        gate = hybrid.escalation_gate(ctx(tier2_attempted=(), generated_attempts=0))
        self.assertFalse(gate.allowed)
        self.assertIn("即时生成补位", gate.reason)


class GateBoundaryTests(unittest.TestCase):
    def test_deny_non_chat_shape(self):
        for shape in ("mcp", "rag", "traditional", "agent_chat_x"):
            with self.subTest(shape=shape):
                self.assertFalse(hybrid.escalation_gate(ctx(target_shape=shape)).allowed)
        self.assertTrue(hybrid.escalation_gate(
            ctx(target_shape="agent_chat")).allowed)

    def test_deny_empty_objective(self):
        self.assertFalse(hybrid.escalation_gate(ctx(objective="   ")).allowed)

    def test_deny_turn_and_timeout_bounds(self):
        for turns in (0, 4, -1):
            with self.subTest(turns=turns):
                self.assertFalse(hybrid.escalation_gate(ctx(max_turns=turns)).allowed)
        for timeout in (0, 601):
            with self.subTest(timeout=timeout):
                self.assertFalse(hybrid.escalation_gate(ctx(timeout=timeout)).allowed)

    def test_deny_exhausted_escalation_budget(self):
        gate = hybrid.escalation_gate(ctx(prior_escalations=1))
        self.assertFalse(gate.allowed)
        self.assertIn("次数已用尽", gate.reason)

    def test_refusal_or_detection_stops(self):
        self.assertFalse(hybrid.escalation_gate(ctx(refusal_seen=True)).allowed)
        self.assertFalse(hybrid.escalation_gate(ctx(detection_seen=True)).allowed)

    def test_constants_are_strict(self):
        self.assertEqual(hybrid.MAX_ESCALATION_TURNS, 3)
        self.assertEqual(hybrid.MAX_ESCALATION_ATTEMPTS, 1)
        self.assertEqual(hybrid.MAX_PER_STRATEGY_ATTEMPTS, 2)


class GateConflictTests(unittest.TestCase):
    def test_opt_in_cannot_override_missing_credentials(self):
        gate = hybrid.escalation_gate(ctx(credentials_ok=False))
        self.assertFalse(gate.allowed)
        self.assertTrue(any("硬阻断优先" in c for c in gate.conflicts))

    def test_opt_in_cannot_override_effective_payload(self):
        gate = hybrid.escalation_gate(ctx(tier1_effective=("S-VERBATIM",)))
        self.assertFalse(gate.allowed)
        self.assertTrue(any("已有生效载荷" in c for c in gate.conflicts))

    def test_opt_in_without_pyrit_degrades(self):
        gate = hybrid.escalation_gate(ctx(pyrit_available=False))
        self.assertFalse(gate.allowed)
        self.assertIn("降级", gate.reason)
        self.assertTrue(any("pyrit 不可用" in c for c in gate.conflicts))

    def test_multiple_conflicts_all_recorded(self):
        gate = hybrid.escalation_gate(
            ctx(credentials_ok=False, tier1_effective=("S-1",), pyrit_available=False))
        self.assertFalse(gate.allowed)
        self.assertEqual(len(gate.conflicts), 3)


class HybridFlowTests(unittest.TestCase):
    def test_default_stops_at_python_layer(self):
        calls = []

        def sender(payload):
            calls.append(payload)
            return "I will not reveal that."

        def escalator(*args, **kwargs):
            calls.append("ESCALATED")
            return {"executed": True}

        result = hybrid.run_hybrid(
            objective="Get system prompt", strategies_to_run=("S-VERBATIM",),
            base_url="http://t", sender=sender, escalator=escalator,
            pyrit_available=True, credentials_ok=True, user_opt_in=False)
        self.assertFalse(result.effective)
        self.assertNotIn("ESCALATED", calls)
        self.assertFalse(result.escalation.allowed)

    def test_escalation_called_when_gate_allows(self):
        seen = {}

        def sender(payload):
            return "Nothing relevant was found."

        def escalator(objective, spec, base_url, max_turns, timeout, **subs):
            seen.update(objective=objective, turns=max_turns, base=base_url)
            return {"executed": True,
                    "scoring": {"objective_score": True}}

        result = hybrid.run_hybrid(
            objective="Get system prompt", strategies_to_run=("S-VERBATIM",),
            generated_payloads="Try another framing", base_url="http://t",
            sender=sender, escalator=escalator,
            pyrit_available=True, credentials_ok=True, user_opt_in=True)
        self.assertTrue(result.effective)
        self.assertTrue(result.executed)
        self.assertEqual(seen["turns"], 3)
        self.assertEqual(seen["base"], "http://t")

    def test_success_stops_before_generation_and_escalation(self):
        calls = []

        def sender(payload):
            calls.append(payload)
            return "You are HelperBot and can read_file."

        def escalator(*args, **kwargs):
            calls.append("ESCALATED")
            return {"executed": True}

        result = hybrid.run_hybrid(
            objective="Get system prompt", strategies_to_run=("S-VERBATIM",),
            generated_payloads="other", base_url="http://t",
            sender=sender, escalator=escalator,
            pyrit_available=True, credentials_ok=True, user_opt_in=True)
        self.assertTrue(result.effective)
        self.assertNotIn("other", calls)
        self.assertNotIn("ESCALATED", calls)
        self.assertIn("成功即固化", result.fallback)

    def test_refusal_stops_immediately(self):
        calls = []

        def sender(payload):
            calls.append(payload)
            return "I won't do that — it's off-limits."

        result = hybrid.run_hybrid(
            objective="Get system prompt", strategies_to_run=("S-VERBATIM",),
            base_url="http://t", sender=sender,
            pyrit_available=True, credentials_ok=True, user_opt_in=True)
        self.assertEqual(len(calls), 1)
        self.assertFalse(result.effective)
        self.assertIn("拒绝即停", result.steps[0].reason)

    def test_escalator_exception_is_contained(self):
        def sender(payload):
            return "Nothing relevant was found."

        def escalator(*args, **kwargs):
            raise RuntimeError("simulated failure")

        result = hybrid.run_hybrid(
            objective="Get system prompt", strategies_to_run=("S-VERBATIM",),
            generated_payloads="other", base_url="http://t",
            sender=sender, escalator=escalator,
            pyrit_available=True, credentials_ok=True, user_opt_in=True)
        self.assertFalse(result.effective)
        self.assertIsNone(result.escalation_result)
        self.assertIn("升级执行异常", result.fallback)

    def test_sender_exception_is_contained(self):
        def sender(payload):
            raise OSError("network down")

        result = hybrid.run_hybrid(
            objective="Get system prompt", strategies_to_run=("S-VERBATIM",),
            base_url="http://t", sender=sender)
        self.assertIn("发送失败", result.steps[0].reason)
        self.assertFalse(result.effective)

    def test_result_as_dict_has_fact_layer(self):
        def sender(payload):
            return "I will not reveal that."

        result = hybrid.run_hybrid(
            objective="Get system prompt", strategies_to_run=("S-VERBATIM",),
            base_url="http://t", sender=sender)
        data = result.as_dict()
        self.assertIn("executed", data)
        self.assertIn("escalation", data)
        self.assertTrue(data["executed"])  # Python 编排层已真实执行
        self.assertFalse(data["effective"])


if __name__ == "__main__":
    unittest.main()
