"""rag-10 Ch11 独立步骤契约证据测试（AC-1/6/7）。"""
import os
import unittest

from tools.attack_rag import AttackRequest, run_ch11
from tools.attack_rag.ch11 import CH11_STEP_IDS
from tools.attack_rag.steps import STEP_IDS as FROZEN_STEP_IDS
from tools.report_exam.index import parse_fragment

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class Ch11ContractTests(unittest.TestCase):
    def test_ac1_frozen_six_ids_untouched_and_ch11_independent(self):
        self.assertEqual(FROZEN_STEP_IDS,
                         ("rag-00", "rag-01", "rag-02", "rag-03", "rag-04", "rag-05"))
        self.assertEqual(CH11_STEP_IDS, ("rag-10",))
        self.assertNotIn("rag-10", FROZEN_STEP_IDS)

    def test_ac6_rag10_evidence_fragment_parseable(self):
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            req = AttackRequest(target="rag-ch11", step="rag-10", evidence_dir=td)
            report = run_ch11(req)
            self.assertEqual([v.step_id for v in report.verdicts], ["rag-10"])
            v = report.verdicts[0]
            self.assertTrue(os.path.isfile(os.path.join(ROOT, v.evidence_path)) or
                            os.path.isfile(v.evidence_path))
            with open(v.evidence_path, encoding="utf-8") as fh:
                text = fh.read()
            frag = parse_fragment(text, v.evidence_path)
            self.assertIsNotNone(frag)

    def test_ac7_kibana_unreachable_undetermined(self):
        # 离线样例不臆断告警状态：run_ch11 输出含 UNDETERMINED 语义标注
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            req = AttackRequest(target="rag-ch11", step="rag-10", evidence_dir=td)
            report = run_ch11(req)
            self.assertIn("UNDETERMINED", report.verdicts[0].output)


if __name__ == "__main__":
    unittest.main()
