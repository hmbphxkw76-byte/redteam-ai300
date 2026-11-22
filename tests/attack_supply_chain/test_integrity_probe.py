"""完整性校验探测 → import 劫持降级测试（Ch11 sc-05b · AC-1/2/3/4）。"""
import unittest

from tools.attack_supply_chain.integrity_probe import (
    probe_integrity, import_hijack_plan, cleanup_steps)


class IntegrityProbeTests(unittest.TestCase):
    def test_ac1_three_state(self):
        guarded = probe_integrity("2025-10-09T10:00", "2025-10-09T10:00", True)
        self.assertEqual(guarded["verdict"], "有校验")
        open_ = probe_integrity("2025-10-09T10:00", "2025-10-09T10:05", False)
        self.assertEqual(open_["verdict"], "无校验")
        und = probe_integrity("", "2025-10-09T10:05", True)
        self.assertEqual(und["verdict"], "UNDETERMINED")

    def test_ac2_import_hijack_no_modify_original(self):
        plan = import_hijack_plan("pandas", backed_up=False)
        joined = " ".join(plan["steps"])
        self.assertIn("备份", joined)
        self.assertIn("不修改原脚本", joined)
        self.assertIn("pandas.py", joined)
        self.assertIn("C1", plan["cleanup_ref"])
        self.assertFalse(plan["backup_done"])

    def test_ac3_cleanup_three_steps_pending(self):
        cl = cleanup_steps("pandas", recovery_verified=False)
        self.assertEqual(len(cl["steps"]), 3)
        self.assertIn("杀 reverse shell", " ".join(cl["steps"]))
        self.assertEqual(cl["cleanup_state"], "pending")
        done = cleanup_steps("pandas", recovery_verified=True)
        self.assertEqual(done["cleanup_state"], "done")
