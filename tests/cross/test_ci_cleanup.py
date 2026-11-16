# -*- coding: utf-8 -*-
"""ci_cleanup 清理器安全契约测试（标准库 unittest，CI S2 可复现）。

覆盖：dry-run 默认、白名单、保留清单、git 跟踪文件保护、符号链接不跟随、
越界临时路径拒绝、幂等、dist 后置清理、verify 残留/交付物断言。
"""
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

from tests._paths import ROOT_PATH as ROOT  # noqa: E402
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import ci_cleanup as cc  # noqa: E402


class CleanupFixture(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="ci-cleanup-test-")
        self.root = Path(self.tmp.name)
        self.tracked = set()

    def tearDown(self):
        self.tmp.cleanup()

    def touch(self, rel, content="x"):
        p = self.root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
        return p

    def mkdir(self, rel):
        p = self.root / rel
        p.mkdir(parents=True, exist_ok=True)
        return p

    def run_cleanup(self, *extra, phase="post", tracked=None):
        argv = [phase, "--root", str(self.root), "--apply"] + list(extra)
        args = cc.build_parser().parse_args(argv)
        if not args.temp_root:
            args.temp_root = [tempfile.gettempdir()]
        # 注入受控跟踪集合（不依赖真实 git 仓库）
        original = cc.load_tracked
        cc.load_tracked = lambda root: (set(tracked or self.tracked), True)
        try:
            return cc.build_report(args)
        finally:
            cc.load_tracked = original


class TestDryRunAndWhitelist(CleanupFixture):
    def test_default_is_dry_run(self):
        pyc = self.touch("tools/mod.pyc")
        args = cc.build_parser().parse_args(["post", "--root", str(self.root)])
        report, code = cc.build_report(args)
        self.assertEqual(code, 0)
        self.assertEqual(report["mode"], "dry-run")
        self.assertTrue(pyc.exists())
        self.assertTrue(any(i["path"] == "tools/mod.pyc" for i in report["workspace_removed"]))

    def test_cache_dirs_and_files_removed(self):
        for rel in ("tools/__pycache__", "tests/__pycache__", ".pytest_cache",
                    ".mypy_cache", ".ruff_cache", "htmlcov", "build", "pkg.egg-info"):
            self.mkdir(rel)
        for rel in ("a.pyc", "b.pyo", ".coverage", ".coverage.host", "coverage.xml"):
            self.touch(rel)
        report, code = self.run_cleanup()
        self.assertEqual(code, 0)
        self.assertEqual(len(report["workspace_removed"]), 13)
        for rel in ("tools/__pycache__", "build", "a.pyc", ".coverage.host"):
            self.assertFalse((self.root / rel).exists(), rel)

    def test_unknown_scratch_not_touched(self):
        self.touch("notes.md")
        self.touch("random.tmp")
        report, _ = self.run_cleanup()
        self.assertTrue((self.root / "notes.md").exists())
        self.assertTrue((self.root / "random.tmp").exists())
        self.assertEqual(report["workspace_removed"], [])


class TestKeepManifest(CleanupFixture):
    def test_tracked_file_inside_cache_dir_protects_whole_dir(self):
        # 缓存型目录内意外存在被跟踪文件时，整目录保护（绝不误删）。
        tracked_cache = self.touch("tools/__pycache__/special.pyc")
        plain_cache = self.touch("tests/__pycache__/normal.pyc")
        self.tracked = {"tools/__pycache__/special.pyc"}
        self.run_cleanup()
        self.assertTrue(tracked_cache.exists())
        self.assertFalse(plain_cache.exists())

    def test_tracked_source_kept_but_plain_cache_cleaned(self):
        # 被跟踪源码永不删；其同目录的普通 .pyc 仍属可清理缓存。
        src = self.touch("tools/live/app.py")
        cache = self.touch("tools/live/app.pyc")
        self.tracked = {"tools/live/app.py"}
        self.run_cleanup()
        self.assertTrue(src.exists())
        self.assertFalse(cache.exists())

    def test_tracked_file_named_like_cache_protected(self):
        tracked_pyc = self.touch("vendor/weird.pyc")
        self.tracked = {"vendor/weird.pyc"}
        self.run_cleanup()
        self.assertTrue(tracked_pyc.exists())

    def test_protected_toplevel_kept(self):
        for rel in (".git/config", ".workbuddy/memory/x.md", "evidence/a.md",
                    "loot/registry.md", ".env", ".venv/bin/python", "node_modules/x/index.js",
                    "dist/redteam-ai300-skills.tgz"):
            self.touch(rel)
        self.run_cleanup()
        for rel in (".git/config", ".workbuddy/memory/x.md", "evidence/a.md",
                    "loot/registry.md", ".env", ".venv/bin/python", "node_modules/x/index.js",
                    "dist/redteam-ai300-skills.tgz"):
            self.assertTrue((self.root / rel).exists(), rel)

    def test_symlink_not_followed(self):
        outside = Path(tempfile.mkdtemp(prefix="ci-cleanup-outside-"))
        self.addCleanup(shutil.rmtree, outside, True)
        (outside / "precious.txt").write_text("keep", encoding="utf-8")
        link = self.root / "__pycache__"
        try:
            link.symlink_to(outside, target_is_directory=True)
        except OSError:
            self.skipTest("symlink unsupported")
        report, _ = self.run_cleanup()
        self.assertTrue((outside / "precious.txt").exists())
        self.assertTrue(link.is_symlink())
        self.assertTrue(any(r["reason"] == "symlink" for r in report["skipped"]))


class TestDistOptIn(CleanupFixture):
    def test_pre_never_cleans_dist(self):
        self.touch("dist/redteam-ai300-skills.tgz")
        self.run_cleanup(phase="pre", extra=["--clean-dist"]) if False else None
        # pre 阶段直接拒绝 --clean-dist（CLI 层）
        self.assertEqual(cc.main(["pre", "--root", str(self.root), "--clean-dist"]), 2)
        self.assertTrue((self.root / "dist/redteam-ai300-skills.tgz").exists())

    def test_dist_clean_only_known_outputs_in_post(self):
        known = self.touch("dist/redteam-ai300-skills.tgz")
        sha = self.touch("dist/redteam-ai300-skills.tgz.sha256")
        foreign = self.touch("dist/other-package.tgz")
        report, _ = self.run_cleanup("--clean-dist")
        self.assertFalse(known.exists())
        self.assertFalse(sha.exists())
        self.assertTrue(foreign.exists())


class TestTempScope(CleanupFixture):
    def test_temp_target_removed_and_other_kept(self):
        tmp_root = self.mkdir("_runner_temp")
        target = tmp_root / "osai_pr_body.md"
        other = tmp_root / "keep.txt"
        target.write_text("x", encoding="utf-8")
        other.write_text("x", encoding="utf-8")
        report, _ = self.run_cleanup(
            "--temp-root", str(tmp_root), "--temp-target", str(target)
        )
        self.assertFalse(target.exists())
        self.assertTrue(other.exists())
        self.assertEqual(len(report["temp_removed"]), 1)

    def test_outside_temp_root_rejected(self):
        other = Path(tempfile.mkdtemp(prefix="ci-cleanup-out-"))
        self.addCleanup(shutil.rmtree, other, True)
        victim = other / "victim.md"
        victim.write_text("x", encoding="utf-8")
        tmp_root = self.mkdir("_runner_temp")
        report, _ = self.run_cleanup(
            "--temp-root", str(tmp_root), "--temp-target", str(victim)
        )
        self.assertTrue(victim.exists())
        self.assertTrue(any(r["reason"] == "outside-temp-root" for r in report["skipped"]))

    def test_temp_root_itself_rejected(self):
        tmp_root = self.mkdir("_runner_temp")
        report, _ = self.run_cleanup(
            "--temp-root", str(tmp_root), "--temp-target", str(tmp_root)
        )
        self.assertTrue(tmp_root.exists())
        self.assertTrue(any(r["reason"] == "temp-root-itself" for r in report["skipped"]))


class TestIdempotencyAndVerify(CleanupFixture):
    def test_second_run_is_noop(self):
        self.touch("a.pyc")
        self.mkdir("tools/__pycache__")
        first, _ = self.run_cleanup()
        second, _ = self.run_cleanup()
        self.assertEqual(len(first["workspace_removed"]), 2)
        self.assertEqual(second["workspace_removed"], [])
        self.assertEqual(second["verdict"], "PASS")

    def test_verify_detects_residue(self):
        self.touch("leftover.pyc")
        args = cc.build_parser().parse_args(["verify", "--root", str(self.root)])
        report, code = cc.build_report(args)
        self.assertEqual(code, 1)
        self.assertEqual(report["verdict"], "FAIL")
        self.assertTrue(any(i["path"] == "leftover.pyc" for i in report["residue"]))

    def test_verify_passes_after_cleanup(self):
        self.touch("a.pyc")
        self.run_cleanup()
        args = cc.build_parser().parse_args(["verify", "--root", str(self.root)])
        report, code = cc.build_report(args)
        self.assertEqual(code, 0)
        self.assertEqual(report["residue"], [])

    def test_verify_asserts_keep_deliverable(self):
        args = cc.build_parser().parse_args([
            "verify", "--root", str(self.root),
            "--keep", str(self.root / "dist/artifact.tgz"),
        ])
        report, code = cc.build_report(args)
        self.assertEqual(code, 1)
        self.assertFalse(report["keep"][0]["present"])

    def test_keep_only_ignores_residue(self):
        # 交付物门禁只断言 keep，不受其他缓存残留影响。
        deliverable = self.touch("dist/redteam-ai300-skills.tgz")
        self.touch("leftover.pyc")
        args = cc.build_parser().parse_args([
            "verify", "--root", str(self.root), "--keep-only",
            "--keep", str(deliverable),
        ])
        report, code = cc.build_report(args)
        self.assertEqual(code, 0)
        self.assertEqual(report["residue"], [])
        self.assertTrue(report["keep"][0]["present"])


class TestHelpers(unittest.TestCase):
    def test_has_tracked_under(self):
        tracked = {"a/b/c.py", "x.txt"}
        self.assertTrue(cc.has_tracked_under("a/b", tracked))
        self.assertTrue(cc.has_tracked_under("a", tracked))
        self.assertTrue(cc.has_tracked_under("a/b/c.py", tracked))
        self.assertFalse(cc.has_tracked_under("d", tracked))

    def test_within(self):
        root = Path("/base/root")
        self.assertTrue(cc._within(Path("/base/root/sub/x"), root))
        self.assertFalse(cc._within(Path("/base/other/x"), root))

    def test_cleanable_file_dist_policy(self):
        self.assertFalse(cc._cleanable_file("redteam-ai300-skills.tgz", "dist/redteam-ai300-skills.tgz", False))
        self.assertTrue(cc._cleanable_file("redteam-ai300-skills.tgz", "dist/redteam-ai300-skills.tgz", True))
        self.assertFalse(cc._cleanable_file("other.tgz", "dist/other.tgz", True))
        self.assertTrue(cc._cleanable_file("m.pyc", "tools/m.pyc", False))


if __name__ == "__main__":
    unittest.main()
