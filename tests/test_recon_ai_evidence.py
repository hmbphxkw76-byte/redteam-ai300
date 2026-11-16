#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""AC-04/AC-13：Windows 编码回归与证据完整性（中文输出不得触发解码失败）。"""
import hashlib
import io
import os
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from tools.recon_ai import evidence  # noqa: E402

COLLECT = os.path.join(ROOT, "tools", "collect_evidence.py")
CHINESE = "中文输出：模型=LongCat-2.5；判定=不可判定"


class EncodingRegressionTests(unittest.TestCase):
    def test_writer_emits_chinese_output_without_decode_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            writer = evidence.EvidenceWriter(
                tmp, manifest=os.path.join(tmp, "MANIFEST.jsonl"))
            path, code, err = writer.emit(
                "recon-01", "curl -s http://t/api/config", CHINESE,
                target="http://t", title="中文标题", strict=False)
            with open(path, encoding="utf-8") as f:
                text = f.read()
            record = evidence.load_manifest(writer.manifest)[0]
        self.assertEqual(code, 0, err)
        self.assertIn("中文输出", text)
        self.assertEqual(record["sha256"],
                         hashlib.sha256(CHINESE.encode("utf-8")).hexdigest())
        self.assertEqual(len(record["sha256"]), 64)

    def test_collector_reads_utf8_stdin(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = os.path.join(tmp, "f.md")
            env = dict(os.environ, PYTHONUTF8="1", PYTHONIOENCODING="utf-8")
            proc = subprocess.run(
                [sys.executable, COLLECT, "--step", "recon-01",
                 "--cmd", "curl -s http://t/api/config", "--out", out,
                 "--output-file", "-", "--shot-cmd", "hook"],
                input=CHINESE.encode("utf-8"), capture_output=True, env=env)
            with io.open(out, encoding="utf-8") as f:
                text = f.read()
        self.assertEqual(proc.returncode, 0, proc.stderr.decode("utf-8", "replace"))
        self.assertIn(CHINESE, text)


class SubprocessRetryTests(unittest.TestCase):
    """一次性异常退出（NTSTATUS/负值 + 空 stderr）只重试一次；质量门失败不重试。"""

    @staticmethod
    def _proc(code, stderr=""):
        return mock.Mock(returncode=code, stderr=stderr)

    def test_abnormal_exit_retries_once(self):
        with tempfile.TemporaryDirectory() as tmp:
            writer = evidence.EvidenceWriter(tmp)
            with mock.patch.object(
                    evidence.subprocess, "run",
                    side_effect=[self._proc(0xC000012D), self._proc(0)]) as run:
                _, code, _ = writer.emit("recon-01", "curl", "out")
        self.assertEqual(code, 0)
        self.assertEqual(run.call_count, 2)

    def test_quality_gate_failure_is_not_retried(self):
        with tempfile.TemporaryDirectory() as tmp:
            writer = evidence.EvidenceWriter(tmp)
            with mock.patch.object(
                    evidence.subprocess, "run",
                    side_effect=[self._proc(1, "quality gate failed")]) as run:
                _, code, err = writer.emit("recon-01", "curl", "out")
        self.assertEqual(code, 1)
        self.assertIn("quality gate", err)
        self.assertEqual(run.call_count, 1)


if __name__ == "__main__":
    unittest.main()
