#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""覆盖率清单完整性：每个技能都必须有可度量的覆盖率目标。

覆盖率门禁见 `docs/standards/CI-CD.md` §3 S2（`measure_coverage.py --target` 与
CI 全量 80% 门槛）；`scripts/tools_manifest.json:coverage_targets` 是目标清单的
单一事实源。若某技能未登记，其覆盖率既无法测量也无法被门禁拦截——
`foothold-traditional` 即因此长期无数据。本用例把「技能 ↔ 目标」的对应关系
固化为可执行断言，避免新增技能时再次漏登。
"""
import json
import unittest

from tests._paths import ROOT_PATH  # noqa: E402

MANIFEST_PATH = ROOT_PATH / "scripts" / "tools_manifest.json"


def _load_targets():
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    return manifest["coverage_targets"]


def _skill_names():
    return sorted(p.parent.name for p in (ROOT_PATH / "skills").glob("*/SKILL.md"))


class CoverageTargetCoverageTests(unittest.TestCase):
    """技能全集与 coverage_targets 必须覆盖一致。"""

    def test_every_skill_has_coverage_target(self):
        declared = {t.get("skill") or t["name"] for t in _load_targets()}
        missing = [s for s in _skill_names() if s not in declared]
        self.assertEqual(missing, [], "以下技能缺覆盖率目标：%s" % "、".join(missing))

    def test_target_names_are_unique(self):
        names = [t["name"] for t in _load_targets()]
        duplicated = sorted({n for n in names if names.count(n) > 1})
        self.assertEqual(duplicated, [], "覆盖率目标重名：%s" % "、".join(duplicated))

    def test_skill_field_names_a_real_skill(self):
        """`skill` 字段用于目标名与技能名不一致时对齐，必须指向真实技能。"""
        skills = set(_skill_names())
        invalid = ["%s → %s" % (t["name"], t["skill"])
                   for t in _load_targets() if t.get("skill") and t["skill"] not in skills]
        self.assertEqual(invalid, [], "skill 字段指向不存在的技能：%s" % "；".join(invalid))

    def test_target_modules_and_tests_exist(self):
        missing = []
        for target in _load_targets():
            for dotted in list(target["modules"]) + list(target["tests"]):
                path = ROOT_PATH.joinpath(*dotted.split("."))
                if not (path.with_suffix(".py").is_file() or (path / "__init__.py").is_file()):
                    missing.append("%s → %s" % (target["name"], dotted))
        self.assertEqual(missing, [], "清单指向不存在的模块：%s" % "；".join(missing))


if __name__ == "__main__":
    unittest.main()
