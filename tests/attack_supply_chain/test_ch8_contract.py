# -*- coding: utf-8 -*-
"""阶段9 TDD：G13 证据契约 + G14 交战规则四标识（对齐矩阵 G13/G14 引用）。

只测外部行为：契约 v3 锚点存在、既有 8 步证据夹具结构、SKILL.md 四条边界标识。
"""
import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)


class TestEvidenceContractV3(unittest.TestCase):
    def test_contract_anchors_present(self):
        path = os.path.join(ROOT, "docs", "contracts", "collect_evidence.contract.md")
        with open(path, encoding="utf-8") as f:
            text = f.read()
        for anchor in ("contract_version", "flag 双通道", "parse_fragment", "shot_status"):
            self.assertIn(anchor, text)

    def test_existing_evidence_fixture(self):
        path = os.path.join(ROOT, "tests", "attack_supply_chain",
                            "test_attack_supply_chain_evidence_contract.py")
        with open(path, encoding="utf-8") as f:
            text = f.read()
        self.assertIn("sc-0%d" % 1, text)
        self.assertIn("sc-08", text)

    def test_build_fragment_flags(self):
        from tools.collect_evidence import build_fragment
        import inspect
        sig = inspect.signature(build_fragment)
        for name in ("flag_panel", "flag_shot", "ai_log", "shot_kind"):
            self.assertIn(name, sig.parameters)


class TestRoeMarkers(unittest.TestCase):
    def test_four_boundary_markers(self):
        path = os.path.join(ROOT, "skills", "attack-supply-chain", "SKILL.md")
        with open(path, encoding="utf-8") as f:
            text = f.read()
        for marker in ("显式授权", "平台判断", "取证痕迹", "被拦截"):
            self.assertIn(marker, text)


if __name__ == "__main__":
    unittest.main()
