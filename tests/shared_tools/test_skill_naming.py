#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""技能命名守卫：osai-orchestrator 是唯一标识。

命名依据：OSAI 本身就是考试，不再需要 exam 后缀。历史旧称只存在于版本历史与
原始证据日志中，不进入受控目录；本用例阻止其回流。
"""
import unittest

from tests._paths import ROOT_PATH  # noqa: E402

# 用拼接构造旧标识，避免本文件自身被扫描命中。
LEGACY = "osai-" + "exam-" + "orchestrator"
CANONICAL = "osai-orchestrator"
SCAN_ROOTS = ("skills", "docs", "scripts", "tests", ".github")
SCAN_SUFFIXES = {".md", ".py", ".json", ".yml", ".yaml", ".toml"}


def _tracked_text_files():
    for root in SCAN_ROOTS:
        path = ROOT_PATH / root
        if not path.is_dir():
            continue
        for item in path.rglob("*"):
            if item.is_file() and item.suffix in SCAN_SUFFIXES:
                yield item


class SkillNamingTests(unittest.TestCase):
    """受控目录中不得出现旧技能标识。"""

    def test_no_legacy_identifier_in_managed_dirs(self):
        hits = []
        for path in _tracked_text_files():
            text = path.read_text(encoding="utf-8", errors="ignore")
            if LEGACY in text:
                hits.append(str(path.relative_to(ROOT_PATH)))
        self.assertEqual(hits, [], "受控目录出现旧技能标识：%s" % "；".join(hits))

    def test_skill_directory_and_frontmatter(self):
        skill = ROOT_PATH / "skills" / CANONICAL / "SKILL.md"
        self.assertTrue(skill.is_file(), "技能目录未使用规范名：%s" % skill)
        text = skill.read_text(encoding="utf-8")
        self.assertIn("name: " + CANONICAL, text, "SKILL.md frontmatter 名称不一致")

    def test_specs_and_gate_records_use_canonical_name(self):
        specs = [ROOT_PATH / "docs" / "specs" / ("%s-spec-v%d.md" % (CANONICAL, v))
                 for v in (1, 2)]
        missing = [str(p.relative_to(ROOT_PATH)) for p in specs if not p.is_file()]
        gates = sorted((ROOT_PATH / "docs" / "operations").glob(CANONICAL + "-gate-stage*.md"))
        self.assertEqual(missing, [], "规格文件缺失：%s" % "；".join(missing))
        self.assertGreaterEqual(len(gates), 10, "阶段门禁记录不足：%d/10" % len(gates))


if __name__ == "__main__":
    unittest.main()
