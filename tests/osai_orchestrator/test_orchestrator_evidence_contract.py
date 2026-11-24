"""证据契约断言：新模块不改写证据片段与 flag 原值块。"""
from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


class EvidenceContractTest(unittest.TestCase):
    def test_collect_evidence_untouched(self):
        path = ROOT / "tools" / "collect_evidence.py"
        self.assertTrue(path.is_file())
        text = path.read_text(encoding="utf-8")
        self.assertIn("三件套", text)
        self.assertIn("strict", text)

    def test_report_exam_parser_untouched_semantics(self):
        path = ROOT / "tools" / "report_exam" / "index.py"
        self.assertTrue(path.is_file())
        text = path.read_text(encoding="utf-8")
        self.assertIn("parse_fragment", text)

    def test_no_existing_skill_modified_by_module(self):
        module = ROOT / "tools" / "osai_orchestrator"
        for py in module.glob("*.py"):
            text = py.read_text(encoding="utf-8")
            self.assertNotIn("http://192.168.40.189", text)
            self.assertNotIn("OPENAI_CHAT_API_KEY", text)

    def test_module_has_no_third_party_imports(self):
        stdlib = {"__future__", "argparse", "json", "re", "subprocess", "sys", "dataclasses",
                  "enum", "typing", "pathlib", "collections", "unittest"}
        for py in (ROOT / "tools" / "osai_orchestrator").glob("*.py"):
            for line in py.read_text(encoding="utf-8").splitlines():
                if line.startswith(("import ", "from ")):
                    name = line.split()[1].split(".")[0]
                    if name in ("osai_orchestrator",) or line.startswith("from ."):
                        continue
                    self.assertIn(name, stdlib, "%s: %s" % (py.name, line))


if __name__ == "__main__":
    unittest.main()
