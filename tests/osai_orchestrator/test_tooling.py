"""工具治理。"""
from __future__ import annotations

import unittest

from tools.osai_orchestrator.models import Verdict
from tools.osai_orchestrator.tooling import (
    BoundedRetriever, CallIDNormalizer, ErrorClassifier, ErrorKind,
    RetrievalHit, RetryPolicy, ToolKind, ToolSpec, TypedRegistry,
)


class TypedRegistryTest(unittest.TestCase):
    def test_register_and_check(self):
        r = TypedRegistry([ToolSpec("terminal", ToolKind.ENVIRONMENT, frozenset({"pentester"}))])
        self.assertIs(r.check("terminal", "pentester")[0], Verdict.PASS)

    def test_role_restricted(self):
        r = TypedRegistry([ToolSpec("terminal", ToolKind.ENVIRONMENT, frozenset({"pentester"}))])
        verdict, msg = r.check("terminal", "searcher")
        self.assertIs(verdict, Verdict.BLOCKED)
        self.assertIn("not allowed", msg)

    def test_unknown_tool(self):
        self.assertIs(TypedRegistry().check("nope", "agent")[0], Verdict.BLOCKED)

    def test_for_role_includes_unrestricted(self):
        r = TypedRegistry([ToolSpec("done", ToolKind.BARRIER)])
        self.assertEqual(len(r.for_role("any")), 1)

    def test_empty_name_rejected(self):
        with self.assertRaises(ValueError):
            TypedRegistry().register(ToolSpec("", ToolKind.AGENT))


class CallIDNormalizerTest(unittest.TestCase):
    def test_normalize_prefixes(self):
        n = CallIDNormalizer()
        self.assertEqual(n.normalize("call_abc123"), "call_abc123")
        self.assertEqual(n.normalize("toolu_xyz"), "call_xyz")
        self.assertIsNone(n.normalize(""))

    def test_repair_arguments(self):
        n = CallIDNormalizer()
        verdict, out = n.repair_arguments('{"a": 1')
        self.assertIs(verdict, Verdict.PASS)
        self.assertTrue(out.endswith("}"))

    def test_empty_arguments(self):
        self.assertIs(CallIDNormalizer().repair_arguments("")[0], Verdict.BLOCKED)


class ErrorClassifierTest(unittest.TestCase):
    def test_deterministic(self):
        c = ErrorClassifier()
        self.assertIs(c.classify("permission denied"), ErrorKind.DETERMINISTIC)
        self.assertIs(c.classify("invalid argument"), ErrorKind.DETERMINISTIC)

    def test_transient(self):
        c = ErrorClassifier()
        self.assertIs(c.classify("connection reset"), ErrorKind.TRANSIENT)
        self.assertIs(c.classify("rate limit exceeded"), ErrorKind.TRANSIENT)

    def test_unknown_is_deterministic(self):
        self.assertIs(ErrorClassifier().classify("weird"), ErrorKind.DETERMINISTIC)


class RetryPolicyTest(unittest.TestCase):
    def test_deterministic_no_retry(self):
        r = RetryPolicy().decide(ErrorKind.DETERMINISTIC, 0)
        self.assertFalse(r.should_retry)
        self.assertIn("deterministic", r.reason)

    def test_transient_bounded(self):
        p = RetryPolicy(2)
        self.assertTrue(p.decide(ErrorKind.TRANSIENT, 0).should_retry)
        self.assertFalse(p.decide(ErrorKind.TRANSIENT, 2).should_retry)

    def test_invalid_ceiling(self):
        with self.assertRaises(ValueError):
            RetryPolicy(0)


class BoundedRetrieverTest(unittest.TestCase):
    def test_local_only(self):
        hits = [
            RetrievalHit("method a", "local://kb/a", True),
            RetrievalHit("method b", "https://external/b", True),
        ]
        kept, dropped = BoundedRetriever().filter(hits)
        self.assertEqual(len(kept), 1)
        self.assertEqual(len(dropped), 1)

    def test_drops_addresses(self):
        hits = [RetrievalHit("scan 10.0.0.1", "local://kb/a", True)]
        kept, dropped = BoundedRetriever().filter(hits)
        self.assertEqual(kept, [])
        self.assertTrue(any("address" in d for d in dropped))

    def test_max_hits(self):
        hits = [RetrievalHit("note %d" % i, "local://kb/%d" % i, True) for i in range(10)]
        kept, _ = BoundedRetriever(max_hits=3).filter(hits)
        self.assertEqual(len(kept), 3)


if __name__ == "__main__":
    unittest.main()
