#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""attack-rag Ch6 probing 复用适配层测试（AC-A1..A3），只测外部行为。"""
import os
import tempfile
import unittest

from tools.attack_rag.ch6_adapter import build_query_iface
from tools.attack_rag.backends import FakeBackend
from tools.attack_rag.harness import RagHarness


class Ch6AdapterTests(unittest.TestCase):
    def setUp(self):
        self.harness = RagHarness(["password reset procedure", "normal policy doc"])

    def test_query_iface_returns_text(self):
        """AC-A1: 可用 backend → 返回非空 str。"""
        iface = build_query_iface(self.harness, FakeBackend(), k=2)
        out = iface("password reset?")
        self.assertIsInstance(out, str)
        self.assertTrue(out)

    def test_no_backend_returns_empty(self):
        """AC-A2: backend=None → 空串、不抛异常。"""
        iface = build_query_iface(self.harness, None, k=2)
        self.assertEqual(iface("anything"), "")

    def test_backend_exception_propagates(self):
        class Broken:
            def respond(self, q, ctx):
                raise RuntimeError("backend down")
        iface = build_query_iface(self.harness, Broken(), k=2)
        with self.assertRaises(RuntimeError):
            iface("q")

    def test_no_side_effect_artifacts(self):
        """AC-A3: 调用不产生文件；harness 文档数不变（公开接口断言）。"""
        before = len(self.harness)
        backend = FakeBackend()
        with tempfile.TemporaryDirectory() as td:
            cwd = os.getcwd()
            try:
                os.chdir(td)
                iface = build_query_iface(self.harness, backend, k=2)
                iface("password reset?")
                self.assertEqual(os.listdir(td), [])
            finally:
                os.chdir(cwd)
        self.assertEqual(len(self.harness), before)
        # backend 自身记录调用属其既有行为，适配层不额外改其状态
        self.assertEqual(len(backend.calls), 1)


if __name__ == "__main__":
    unittest.main()
