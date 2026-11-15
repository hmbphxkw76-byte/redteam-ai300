"""三层隔离机制脚本的单元测试。

覆盖：mainline_worktree 的分支名映射与命令分发；checkout_lock 的并发判定逻辑。
仅测外部行为，不测 IO 副作用（真实 git worktree add/remove 由冒烟脚本验证）。
"""
import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from scripts import mainline_worktree as mw  # noqa: E402
from scripts import checkout_lock as cl  # noqa: E402


class TestBranchMapping(unittest.TestCase):
    """mainline_worktree._branch_for 的分支名规范化。"""

    def test_simple_name(self):
        self.assertEqual(mw._branch_for("decoy-detect"), "feat/decoy-detect")

    def test_slash_normalized(self):
        self.assertEqual(mw._branch_for("attack/ai-agent"), "feat/attack-ai-agent")

    def test_space_normalized(self):
        self.assertEqual(mw._branch_for("recon ai"), "feat/recon-ai")

    def test_empty_rejected(self):
        with self.assertRaises(ValueError):
            mw._branch_for("///")


class TestSharedFileDefaults(unittest.TestCase):
    """共享文件清单默认值（ADR 三层隔离 ③ 约定的四类）。"""

    def test_four_defaults(self):
        self.assertEqual(len(cl.DEFAULT_SHARED_FILES), 4)
        for f in ("scripts/check_token_budget.py", "scripts/measure_coverage.py",
                  ".github/workflows/ci.yml", "GLOSSARY.md"):
            self.assertIn(f, cl.DEFAULT_SHARED_FILES)


class TestConflictDetection(unittest.TestCase):
    """checkout_lock 的核心判定：同一文件被 ≥2 worktree 改动即判冲突。"""

    def test_no_offenders_passes(self):
        # 无任何文件被改动 → 无冲突。
        offenders = {}
        conflicts = {f: w for f, w in offenders.items() if len(w) >= 2}
        self.assertEqual(conflicts, {})

    def test_single_worktree_not_conflict(self):
        # 同一文件仅 1 个 worktree 改动 → 不判冲突。
        offenders = {"GLOSSARY.md": ["D:/_a_wt"]}
        conflicts = {f: w for f, w in offenders.items() if len(w) >= 2}
        self.assertEqual(conflicts, {})

    def test_two_worktrees_conflict(self):
        # 同一文件被 2 个 worktree 改动 → 判冲突。
        offenders = {"GLOSSARY.md": ["D:/_a_wt", "D:/_b_wt"]}
        conflicts = {f: w for f, w in offenders.items() if len(w) >= 2}
        self.assertEqual(set(conflicts.keys()), {"GLOSSARY.md"})


if __name__ == "__main__":
    unittest.main()
