"""工具校验落差判定 + SQL→OS 升级测试（Ch3 模板 4 · AC-1/2/3/4/5）。"""
import unittest

from tools.attack_ai_agent.validation_gap import (
    assess_validation_gap, sql_to_os_escalation, no_gap_downgrade_advice,
    root_cause_attribution)


class ValidationGapTests(unittest.TestCase):
    def test_ac1_three_state_no_fabrication(self):
        gap = assess_validation_gap("read-only SELECT", ["EXEC sp_configure 'xp_cmdshell', 1"])
        self.assertEqual(gap["verdict"], "有落差")
        none = assess_validation_gap("read-only SELECT", ["SELECT 1"])
        self.assertEqual(none["verdict"], "无落差")
        und = assess_validation_gap("", ["EXEC xp_cmdshell 'ver'"])
        self.assertEqual(und["verdict"], "UNDETERMINED")

    def test_ac2_sql_to_os_escalation_steps(self):
        steps = sql_to_os_escalation()
        self.assertGreaterEqual(len(steps), 3)
        joined = " ".join(s["command"] for s in steps)
        self.assertIn("sp_configure", joined)
        self.assertIn("xp_cmdshell", joined)
        for s in steps:
            self.assertTrue(s["source"], "每步须含来源标注")
            self.assertTrue("不伪造" in s["verify"] or "证据" in s["verify"])

    def test_ac3_no_gap_downgrade(self):
        self.assertIn("D7", no_gap_downgrade_advice())

    def test_ac4_undetermined_not_blocking_and_root_cause(self):
        und = assess_validation_gap("read-only", ["EXEC xp_cmdshell 'ver'"], evidence_available=False)
        self.assertEqual(und["verdict"], "UNDETERMINED")
        self.assertIn("unvalidated", root_cause_attribution())


if __name__ == "__main__":
    unittest.main()
