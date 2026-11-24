"""交接一致性与对齐矩阵测试（阶段 9 TDD）。"""
from __future__ import annotations

import unittest

from tools.osai_orchestrator.handoff import (
    derive_panel_flags,
    recon_fragments_for_report,
    check_h1_asset_inventory,
    check_h2_screenshot,
    check_h3_dual_channel,
    check_h4_reusable_loot,
    check_h5_report_enumeration,
    check_h6_submission,
    ALIGNMENT_CLAIMS,
    verify_alignment,
)
from tools.osai_orchestrator.models import Verdict


class PanelFlagsTest(unittest.TestCase):
    def test_derives_panel_value_only(self):
        text = "| L-1 | flag | X | host2 | loot/a.md | t | 已取证 | 面板=PANEL1；截图=evidence/a.png |"
        flags = derive_panel_flags(text)
        self.assertEqual(flags, {"host2": "PANEL1"})
        self.assertNotIn("evidence/a.png", flags.values())

    def test_no_panel_returns_empty(self):
        self.assertEqual(derive_panel_flags("| L-1 | flag | X | h | loot/a.md | t | 已取证 | — |"), {})

    def test_malformed_row_blocked_marker(self):
        flags, problems = derive_panel_flags("| broken | row |", with_problems=True)
        self.assertEqual(flags, {})
        self.assertTrue(problems)


class ReconMappingTest(unittest.TestCase):
    def test_recon_kept_by_host(self):
        frags = [{"step": "recon-01", "host": "host2", "source": "synthetic"}]
        out = recon_fragments_for_report(frags, ["host2"])
        self.assertEqual(len(out), 1)

    def test_unrelated_host_dropped(self):
        frags = [{"step": "recon-01", "host": "host9", "source": "synthetic"}]
        self.assertEqual(recon_fragments_for_report(frags, ["host2"]), [])

    def test_synthetic_not_filtered(self):
        frags = [{"step": "recon-01", "host": "host2", "source": "synthetic"}]
        self.assertEqual(len(recon_fragments_for_report(frags, ["host2"], real_only=True)), 1)


class HandoffChecksTest(unittest.TestCase):
    def test_h1_blocks_missing_fields(self):
        g = check_h1_asset_inventory([{"asset_id": "a"}], [])
        self.assertIs(g.verdict, Verdict.BLOCKED)
        self.assertTrue(any("category" in f for f in g.findings))

    def test_h1_passes_full_and_keeps_undetermined(self):
        asset = {"asset_id": "a", "category": "agent系统", "product": "p", "version": "v",
                 "endpoint": "e", "credential_hint": "", "evidence_step": "recon-01",
                 "existence": "不可判定"}
        g = check_h1_asset_inventory([asset], [])
        self.assertIs(g.verdict, Verdict.PASS)
        self.assertIn("不可判定", g.evidence)

    def test_h2_blocks_shot_cmd_only(self):
        g = check_h2_screenshot({"screenshot": "", "shot_cmd": "screenshot.py", "scored": True})
        self.assertIs(g.verdict, Verdict.BLOCKED)

    def test_h2_passes_real_file(self):
        g = check_h2_screenshot({"screenshot": "evidence/a.png", "shot_cmd": "", "scored": True})
        self.assertIs(g.verdict, Verdict.PASS)

    def test_h3_blocks_path_as_panel(self):
        g = check_h3_dual_channel("面板=evidence/a.png；截图=evidence/a.png")
        self.assertIs(g.verdict, Verdict.BLOCKED)

    def test_h3_passes_distinct_values(self):
        g = check_h3_dual_channel("面板=PANEL1；截图=evidence/a.png")
        self.assertIs(g.verdict, Verdict.PASS)

    def test_h4_blocks_invalid(self):
        g = check_h4_reusable_loot({"status": "失效", "asset_id": "a"})
        self.assertIs(g.verdict, Verdict.BLOCKED)

    def test_h4_passes_valid(self):
        g = check_h4_reusable_loot({"status": "有效", "asset_id": "a"})
        self.assertIs(g.verdict, Verdict.PASS)

    def test_h5_blocks_recon_dropped(self):
        g = check_h5_report_enumeration(["trad-01"], [], ["host2"])
        self.assertIs(g.verdict, Verdict.BLOCKED)

    def test_h5_passes_with_recon(self):
        g = check_h5_report_enumeration(["trad-01", "recon-01"], ["recon-01"], ["host2"])
        self.assertIs(g.verdict, Verdict.PASS)

    def test_h6_blocks_any_failure(self):
        g = check_h6_submission(assets_ok=False, window_ok=True, encryption_ok=True)
        self.assertIs(g.verdict, Verdict.BLOCKED)
        self.assertIn("断图", " ".join(g.findings))

    def test_h6_blocks_missing_window(self):
        g = check_h6_submission(assets_ok=True, window_ok=False, encryption_ok=True)
        self.assertIs(g.verdict, Verdict.BLOCKED)

    def test_h6_blocks_encryption(self):
        g = check_h6_submission(assets_ok=True, window_ok=True, encryption_ok=False)
        self.assertIs(g.verdict, Verdict.BLOCKED)

    def test_h6_passes(self):
        g = check_h6_submission(assets_ok=True, window_ok=True, encryption_ok=True)
        self.assertIs(g.verdict, Verdict.PASS)


class AlignmentTest(unittest.TestCase):
    def test_claims_cover_candidate_a(self):
        required = {"A1", "A2", "A3", "A4", "A5", "A6", "A7", "A8"}
        self.assertTrue(required.issubset(set(ALIGNMENT_CLAIMS)))

    def test_verify_alignment_pass(self):
        missing = verify_alignment(ALIGNMENT_CLAIMS, set(ALIGNMENT_CLAIMS))
        self.assertEqual(missing, [])

    def test_verify_alignment_detects_gap(self):
        missing = verify_alignment(ALIGNMENT_CLAIMS, {"A1"})
        self.assertIn("A2", missing)


if __name__ == "__main__":
    unittest.main()
