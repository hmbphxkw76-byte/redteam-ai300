"""check_token_budget.py 的零依赖单元测试（对齐 ADR-0003 / CI S2）。"""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import check_token_budget as ctb  # noqa: E402


class EstimateTokensTests(unittest.TestCase):
    def test_ascii_four_chars_per_token(self):
        self.assertEqual(ctb.estimate_tokens("abcd"), 1)
        self.assertEqual(ctb.estimate_tokens("abcdefghi"), 3)

    def test_wide_chars_one_per_token(self):
        self.assertEqual(ctb.estimate_tokens("中文"), 2)
        self.assertEqual(ctb.estimate_tokens("中文abcd"), 3)

    def test_empty_and_monotonic(self):
        self.assertEqual(ctb.estimate_tokens(""), 0)
        self.assertGreater(ctb.estimate_tokens("a" * 100), ctb.estimate_tokens("a" * 10))


class BudgetRulesTests(unittest.TestCase):
    def test_explicit_path_takes_precedence_over_glob(self):
        self.assertEqual(
            ctb.budget_for("docs/operations/skill-mainline-workflow.md"), 28000
        )
        self.assertEqual(ctb.budget_for("docs/operations/domain.md"), 17000)

    def test_report_exam_has_its_own_cap(self):
        self.assertEqual(ctb.budget_for("skills/report-exam/SKILL.md"), 21000)
        self.assertEqual(ctb.budget_for("skills/recon-ai/SKILL.md"), 12000)

    def test_unmanaged_file_has_no_cap(self):
        self.assertIsNone(ctb.budget_for("README.md"))

    def test_cold_classification(self):
        self.assertTrue(ctb.is_cold("docs/standards/cross-ide-mainline-workflow.md"))
        self.assertTrue(ctb.is_cold("skills/report-exam/templates/osai-report-template-en.md"))
        self.assertTrue(ctb.is_cold(".workbuddy/memory/2026-11-14.md"))
        self.assertFalse(ctb.is_cold("docs/governance/GOVERNANCE.md"))
        self.assertFalse(ctb.is_cold("AGENTS.md"))

    def test_over_budget_is_actually_blocked(self):
        """反例：把上限压到 1 字节，--check 必须返回 1，证明门禁无假阴性。"""
        original = dict(ctb.BUDGETS)
        try:
            ctb.BUDGETS.clear()
            ctb.BUDGETS["AGENTS.md"] = 1
            self.assertEqual(ctb.main(["--check"]), 1)
        finally:
            ctb.BUDGETS.clear()
            ctb.BUDGETS.update(original)


class ContractTests(unittest.TestCase):
    def test_current_repo_contracts_are_complete(self):
        self.assertEqual(ctb.check_contracts(), [])

    def test_missing_anchors_are_detected(self):
        """反例：空根目录下契约必须全部报缺失，证明契约检查无假阴性。"""
        with tempfile.TemporaryDirectory() as tmp:
            missing = ctb.check_contracts(Path(tmp))
        self.assertEqual(len(missing), len(ctb.CONTRACTS))

    def test_single_missing_anchor_is_named(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for rel, needle in ctb.CONTRACTS:
                target = root / rel
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(needle, encoding="utf-8")
            (root / "AGENTS.md").write_text("内容被清空", encoding="utf-8")
            missing = ctb.check_contracts(root)
        self.assertTrue(any("AGENTS.md" in item for item in missing))
        self.assertLess(len(missing), len(ctb.CONTRACTS))


class ArtifactTests(unittest.TestCase):
    def test_within_limit_passes(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "brief.md"
            path.write_text("简短简报", encoding="utf-8")
            ok, size, cap = ctb.check_artifact("agent-brief", path)
        self.assertTrue(ok)
        self.assertLessEqual(size, cap)

    def test_over_limit_is_blocked(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "issue.md"
            path.write_bytes(b"x" * 500)
            ok, size, cap = ctb.check_artifact("issue-summary", path)
        self.assertFalse(ok)
        self.assertEqual((size, cap), (500, 400))

    def test_unknown_kind_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(KeyError):
                ctb.check_artifact("unknown", Path(tmp) / "x.md")

    def test_cli_artifact_reflects_judgement(self):
        with tempfile.TemporaryDirectory() as tmp:
            small = Path(tmp) / "small.md"
            large = Path(tmp) / "large.md"
            small.write_text("ok", encoding="utf-8")
            large.write_bytes(b"x" * 500)
            self.assertEqual(ctb.main(["--artifact", "issue-summary", str(small)]), 0)
            self.assertEqual(ctb.main(["--artifact", "issue-summary", str(large)]), 1)


class DuplicateDetectionTests(unittest.TestCase):
    def test_identical_long_paragraph_is_reported_once(self):
        block = "重复段落 " * 60  # 归一化后约 299 字符，超过 MIN_DUP_CHARS
        with tempfile.TemporaryDirectory(dir=ROOT) as tmp:
            a = Path(tmp) / "a.md"
            b = Path(tmp) / "b.md"
            a.write_text(block + "\n\n独有内容\n", encoding="utf-8")
            b.write_text(block + "\n\n另一段独有内容\n", encoding="utf-8")
            wasted, hits = ctb.duplicate_blocks([a, b])
        self.assertEqual(len(hits), 1)
        self.assertGreater(wasted, 0)
        self.assertEqual(len(hits[0][2]), 2)

    def test_short_paragraph_is_ignored(self):
        with tempfile.TemporaryDirectory(dir=ROOT) as tmp:
            a = Path(tmp) / "a.md"
            b = Path(tmp) / "b.md"
            a.write_text("短句\n", encoding="utf-8")
            b.write_text("短句\n", encoding="utf-8")
            _, hits = ctb.duplicate_blocks([a, b])
        self.assertEqual(hits, [])


class CliSmokeTests(unittest.TestCase):
    def test_report_mode_exits_zero(self):
        self.assertEqual(ctb.main(["--report"]), 0)

    def test_check_mode_passes_current_baseline(self):
        self.assertEqual(ctb.main(["--check"]), 0)


if __name__ == "__main__":
    unittest.main()
