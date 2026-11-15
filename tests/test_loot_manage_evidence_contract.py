#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""loot-manage 证据契约测试（S2，AC-5 / AC-11）。

断言：登记簿引用的证据片段由 `collect_evidence.build_fragment` 产出时——
  - 三件套齐全 → `validate --check-pieces` 通过；
  - 缺截图 → `validate --check-pieces` 失败（阻断）。
仅依赖标准库。
"""
import contextlib
import io
import os
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from tools import collect_evidence as ce  # noqa: E402
from tools.loot_manage import cli  # noqa: E402

HEADER = "| 编号 | 类型 | 内容 | 来源主机 | 证据片段路径 | 时间戳 | 状态 | 双通道 |"
SEP = "|---|---|---|---|---|---|---|---|"


def _registry_with(evidence_rel):
    return "\n".join([
        HEADER, SEP,
        "| L-1 | 凭据 | u:p | 10.0.0.1 | %s | 2026-11-15T10:00:00+08:00 | 有效 | — |"
        % evidence_rel,
        "", "## 攻击路径", "", "- 入口 10.0.0.1 → 10.0.0.2",
    ])


class EvidenceContractTests(unittest.TestCase):
    def _run_validate(self, root, registry_path):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = cli.main(["--registry", registry_path, "--root", root,
                           "validate", "--check-pieces"])
        return rc, buf.getvalue()

    def test_complete_fragment_passes(self):
        with tempfile.TemporaryDirectory() as t:
            os.makedirs(os.path.join(t, "loot"))
            shot = os.path.join(t, "s.png")
            with open(shot, "wb") as f:
                f.write(b"\x89PNG\r\n\x1a\n")
            md, report = ce.build_fragment(
                "demo-01", "nmap -sV 10.0.0.1", output="22/tcp open ssh",
                screenshot=shot, target="10.0.0.1")
            self.assertTrue(report["complete"])
            with open(os.path.join(t, "loot", "demo-01.md"), "w", encoding="utf-8") as f:
                f.write(md)
            regp = os.path.join(t, "loot", "registry.md")
            with open(regp, "w", encoding="utf-8") as f:
                f.write(_registry_with("loot/demo-01.md"))
            rc, out = self._run_validate(t, regp)
            self.assertEqual(rc, 0, out)

    def test_incomplete_fragment_blocks(self):
        with tempfile.TemporaryDirectory() as t:
            os.makedirs(os.path.join(t, "loot"))
            md, report = ce.build_fragment("demo-02", "whoami")  # 缺输出与截图
            self.assertFalse(report["complete"])
            with open(os.path.join(t, "loot", "demo-02.md"), "w", encoding="utf-8") as f:
                f.write(md)
            regp = os.path.join(t, "loot", "registry.md")
            with open(regp, "w", encoding="utf-8") as f:
                f.write(_registry_with("loot/demo-02.md"))
            rc, out = self._run_validate(t, regp)
            self.assertEqual(rc, 1, out)
            self.assertIn("三件套不全", out)


if __name__ == "__main__":
    unittest.main()
