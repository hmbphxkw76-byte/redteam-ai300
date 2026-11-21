#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Ch5 增量步骤证据契约：真实 collect_evidence.py 严格模式 + report_exam 解析兼容。"""
import os
import re
import shlex
import subprocess
import sys
import tempfile
import unittest

from tools.attack_rag import AttackRequest, FakeBackend, Runtime, run_ch5
from tools.attack_rag.ch5 import CH5_STEP_IDS
from tools.attack_rag.evidence import EvidenceWriter
from tests._paths import ROOT  # noqa: E402

TOOL = os.path.join(ROOT, "tools", "collect_evidence.py")
REQUIRED = ("#### 确切命令", "#### 关键输出", "#### 截图（访问证明）",
            "#### 证据校验（五件套 / 三件套）", "**三件套齐全**：是。")


class Ch5EvidenceContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.dir = cls.tmp.name
        cls.report = run_ch5(
            AttackRequest(target="rag-ch5", evidence_dir=cls.dir),
            Runtime(backend=FakeBackend(),
                    writer=EvidenceWriter(cls.dir, tool_path=TOOL)))

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def _read(self, sid):
        path = os.path.join(self.dir, "%s.md" % sid)
        self.assertTrue(os.path.isfile(path), "缺少证据片段 %s" % path)
        with open(path, encoding="utf-8") as handle:
            return handle.read()

    def test_all_ch5_steps_emitted(self):
        self.assertEqual([v.step_id for v in self.report.verdicts], list(CH5_STEP_IDS))

    def test_three_pieces_per_step(self):
        for sid in CH5_STEP_IDS:
            text = self._read(sid)
            for section in REQUIRED:
                self.assertIn(section, text, "%s 缺 %s" % (sid, section))

    def test_upload_manifest_and_trace_visibility(self):
        self.assertIn("upload_manifest", self._read("rag-07"))
        self.assertIn("trace_visibility", self._read("rag-09"))

    def test_emitted_command_is_runnable(self):
        """证据「确切命令」须可 copy/paste 复现（B5）：指向 ch5_cli.py 且退出 0。"""
        for sid in CH5_STEP_IDS:
            text = self._read(sid)
            match = re.search(r"```bash\n(.+?)\n```", text, re.DOTALL)
            self.assertIsNotNone(match, "%s 无 bash 围栏命令" % sid)
            command = match.group(1).strip()
            self.assertIn("ch5_cli.py", command, "%s 命令未指向 ch5_cli.py" % sid)
            argv = shlex.split(command)
            if argv and os.path.basename(argv[0]) in ("python", "python3", "py"):
                argv = argv[1:]          # 以当前解释器替换证据命令中的 python
            proc = subprocess.run([sys.executable] + argv + ["--no-emit"], cwd=ROOT,
                                  capture_output=True, text=True, timeout=30)
            self.assertEqual(proc.returncode, 0,
                             "%s 证据命令执行失败：%s" % (sid, proc.stderr[-200:]))

    def test_parse_fragment_compatible(self):
        from tools.report_exam.index import parse_fragment
        for sid in CH5_STEP_IDS:
            parsed = parse_fragment(self._read(sid))
            self.assertTrue(parsed, "%s 解析为空" % sid)


if __name__ == "__main__":
    unittest.main()
