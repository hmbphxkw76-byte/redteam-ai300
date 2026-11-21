#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""attack-ai-agent Ch3 对齐文本契约夹具（主线阶段 8/9）。

机器强制：SKILL.md 行为规格含 Ch3 五步闭环五环、六组技法锚点、
UNDETERMINED 异常语义与 Ch3 章节锚点；保证规格不会被后续改动静默回退。

只测外部行为（规格文本可观察性），不断言 runner/steps 实现细节；
aia-01..12 冻结契约由 test_attack_ai_agent_evidence_contract.py 另行保证。
仅依赖标准库（unittest）。运行：python -m unittest discover -s tests -t .
"""
import os
import unittest

from tests._paths import ROOT  # noqa: E402

SKILL = os.path.join(ROOT, "skills", "attack-ai-agent", "SKILL.md")

# 五步闭环五环（Ch3 §3.1）
LOOP_STAGES = ("Enumerate", "Attack, naive", "Detect", "Evade", "Confirm")
# 六组技法锚点（Ch3 §3.2 / §3.3 / §3.4 / §3.5）
TECHNIQUE_ANCHORS = {
    "系统提示情报": ("系统提示情报提取", "场景化框架"),
    "输出过滤绕过": ("ROT13", "base64/hex"),
    "目标劫持": ("干净重构", "crescendo"),
    "间接注入四技法": ("跨文档分片", "CSS 视觉隐藏", "Unicode 隐藏", "导入解析外泄"),
    "记忆攻击高阶": ("作战相关性判据", "共享数据存储投毒", "recency bias", "会话枚举"),
    "Capstone 验收": ("Capstone", "无 ELK 告警"),
}
# Ch3 章节锚点
CH3_ANCHORS = ("§3.1", "§3.2", "§3.3", "§3.4", "§3.5")


class Ch3ContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with open(SKILL, encoding="utf-8") as f:
            cls.skill = f.read()

    def test_five_step_loop_all_stages_present(self):
        for stage in LOOP_STAGES:
            with self.subTest(stage=stage):
                self.assertIn(stage, self.skill,
                              "五步闭环缺环节 %s（Ch3 §3.1）" % stage)

    def test_technique_anchors_present(self):
        for group, anchors in TECHNIQUE_ANCHORS.items():
            for anchor in anchors:
                with self.subTest(group=group, anchor=anchor):
                    self.assertIn(anchor, self.skill,
                                  "%s 缺技法锚点 %s" % (group, anchor))

    def test_undetermined_semantics_present(self):
        self.assertIn("UNDETERMINED", self.skill,
                      "SIEM 不可达须记 UNDETERMINED（Ch3 §3.1 Info）")
        self.assertIn("不臆断无告警", self.skill,
                      "不得臆造无告警结论（Ch3 §3.1）")

    def test_detection_evidence_in_quality_gate(self):
        self.assertIn("检测证据", self.skill,
                      "质量门须含 detect/confirm 检测证据（AC-11）")
        self.assertIn("规则名与盲点", self.skill,
                      "证据须写明规则名与盲点（Ch3 §3.1 Evade）")

    def test_ch3_section_anchors_present(self):
        for anchor in CH3_ANCHORS:
            with self.subTest(anchor=anchor):
                self.assertIn(anchor, self.skill,
                              "缺 Ch3 依据锚点 %s（AC-13 可追溯性）" % anchor)

    def test_skill_byte_budget(self):
        size = len(self.skill.encode("utf-8"))
        self.assertLessEqual(size, 12000,
                             "SKILL.md 超 C4 预算：%d > 12000" % size)


if __name__ == "__main__":
    unittest.main()
