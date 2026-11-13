#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""校验器自测（S2）。

以临时夹具构造「合规/不合规」技能，验证 validate_skill.py 与 check_glossary.py
能正确放行与拦截，保证流水线自身判定可靠。仅依赖标准库（unittest）。
运行：python -m unittest discover -s tests
"""
import os
import subprocess
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VALIDATE = os.path.join(ROOT, "scripts", "validate_skill.py")
GLOSSARY_CHECK = os.path.join(ROOT, "scripts", "check_glossary.py")

VALID_SKILL = """\
---
name: recon-ai
priority: P0
domain: D2
scoring_unit: 通用
trigger: 目标环境已接入
input: 目标网段
output: AI 资产清单
---
# recon-ai

## 执行体
枚举目标环境中的 AI 组件、ML 基础设施与模型服务。

## 质量门
输出结构化证据（命令 + 输出 + 截图）。

## 校验标准
资产清单可被后续技能直接复用。

## 失败与豁免
无。
"""


def run(script, *args):
    return subprocess.run(
        [sys.executable, script] + list(args),
        cwd=ROOT, capture_output=True, text=True,
    )


class ValidatorTests(unittest.TestCase):
    def test_validator_accepts_valid_skill(self):
        with tempfile.TemporaryDirectory() as tmp:
            skills = os.path.join(tmp, "skills")
            os.makedirs(os.path.join(skills, "recon-ai"))
            with open(os.path.join(skills, "recon-ai", "SKILL.md"), "w", encoding="utf-8") as f:
                f.write(VALID_SKILL)
            r = run(VALIDATE, "--skills-dir", skills)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            self.assertIn("PASS", r.stdout)

    def test_validator_rejects_invalid_skill(self):
        with tempfile.TemporaryDirectory() as tmp:
            skills = os.path.join(tmp, "skills")
            os.makedirs(os.path.join(skills, "bad-skill"))
            with open(os.path.join(skills, "bad-skill", "SKILL.md"), "w", encoding="utf-8") as f:
                f.write("---\nname: bad-skill\npriority: P9\n---\n# x\n")
            r = run(VALIDATE, "--skills-dir", skills)
            self.assertEqual(r.returncode, 1)
            self.assertIn("bad-skill", r.stdout)
            self.assertIn("priority", r.stdout)

    def test_glossary_checker_flags_avoid_term(self):
        with tempfile.TemporaryDirectory() as tmp:
            glossary = os.path.join(tmp, "GLOSSARY.md")
            with open(glossary, "w", encoding="utf-8") as f:
                f.write("**诱饵机**:\n计分外主机。\n_Avoid_: rabbit hole、蜜罐\n")
            scan = os.path.join(tmp, "scan")
            os.makedirs(scan)
            with open(os.path.join(scan, "a.md"), "w", encoding="utf-8") as f:
                f.write("此处是 rabbit hole。")
            r = run(GLOSSARY_CHECK, "--glossary", glossary, "--scan", scan)
            self.assertEqual(r.returncode, 1)
            self.assertIn("rabbit hole", r.stdout)


if __name__ == "__main__":
    unittest.main()
