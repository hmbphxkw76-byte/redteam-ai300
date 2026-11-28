#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""审计修复防回流守卫（R02 AD 链命名/状态回写、R05 冷备清单覆盖）。

断言均读真实仓库文件/常量，不 mock；任一回流即红。
"""
import importlib.util
import unittest
from fnmatch import fnmatch

from tests._paths import ROOT_PATH  # noqa: E402


def _read(rel):
    return (ROOT_PATH / rel).read_text(encoding="utf-8")


def _cold_globs():
    path = ROOT_PATH / "scripts" / "check_token_budget.py"
    spec = importlib.util.spec_from_file_location("_budget_guard", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.COLD_GLOBS


class ADChainAlignmentTests(unittest.TestCase):
    """R02：foothold-ad 须被编排链各处显式承接，状态回写不得滞后。"""

    def test_target_map_t8_maps_foothold_ad(self):
        text = _read("docs/operations/osai-target-map.md")
        t8 = next(ln for ln in text.splitlines() if ln.startswith("| T8 "))
        self.assertIn("foothold-ad", t8, "T8 域控应映射 foothold-ad（GOVERNANCE §4.4）")

    def test_governance_pipeline_names_foothold_ad(self):
        text = _read("docs/governance/GOVERNANCE.md")
        section = text.split("### 4.5", 1)[1].split("## 第五章", 1)[0]
        self.assertIn("foothold-ad", section, "§4.5 域控收敛阶段须点名 foothold-ad")

    def test_trad08_handoff_lists_foothold_ad(self):
        text = _read("skills/foothold-traditional/SKILL.md")
        self.assertIn("foothold-ad", text, "trad-08 移交清单须列 foothold-ad 接收方")

    def test_foothold_ad_mainline_status_not_stale(self):
        text = _read("skills/foothold-ad/SKILL.md")
        self.assertNotIn("阶段 1–11 待补", text, "主线已 PASS，不得残留「待补」滞后声明")

    def test_capstone_not_force_partial_foothold_ad(self):
        text = _read("skills/capstone-rehearse/SKILL.md")
        self.assertNotIn("阶段 1–11 待补", text, "foothold-ad 门禁齐全，capstone 不得强制 PARTIAL")


class ColdGlobCoverageTests(unittest.TestCase):
    """R05：C3 冷备口径须落地——门禁记录与技能示例默认不加载。"""

    def test_gate_records_are_cold(self):
        globs = _cold_globs()
        sample = "docs/operations/attack-rag-gate-stage2.md"
        self.assertTrue(any(fnmatch(sample, g) for g in globs),
                        "COLD_GLOBS 须覆盖阶段门禁记录（AGENTS.md C3）")

    def test_skill_examples_are_cold(self):
        globs = _cold_globs()
        sample = "skills/threat-model/examples/sample.md"
        self.assertTrue(any(fnmatch(sample, g) for g in globs),
                        "COLD_GLOBS 须覆盖 skills/*/examples/*.md（AGENTS.md C3）")


class ContractGateFailClosedTests(unittest.TestCase):
    """R10：契约 PR 门禁不得 fail-open（ADR-0007 ③「未声明即阻断」）。"""

    def test_contract_pr_gate_does_not_swallow_errors(self):
        text = _read(".github/workflows/ci.yml")
        block = text.split("契约 PR 变更清单门禁", 1)[1].split("- name:", 1)[0]
        self.assertNotIn("|| true", block,
                         "契约 PR 门禁 fetch/diff 不得 || true 静默放行（ADR-0007 ③ fail-closed）")


class LootRegistryClassificationTests(unittest.TestCase):
    """R01：入库登记簿须声明演练夹具分类，防真实考试战利品误入公开仓。"""

    def test_registry_declares_rehearsal_classification(self):
        text = _read("loot/registry.md")
        self.assertIn("演练靶场夹具", text,
                      "registry.md 须声明数据分类（R01）：入库仅限演练夹具，真实考试值 gitignored")


if __name__ == "__main__":
    unittest.main()