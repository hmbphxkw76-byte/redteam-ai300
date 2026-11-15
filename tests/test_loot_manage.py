#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""loot-manage 单元测试（S2）：登记簿解析 / 校验 / 登记 / 初始化。

只测外部行为：`validate()` 返回 dict、CLI 退出码、登记簿文本结构。
运行：python -m unittest discover -s tests
"""
import os
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from tools.loot_manage import registry as reg  # noqa: E402
from tools.loot_manage import cli  # noqa: E402

HEADER = "| 编号 | 类型 | 内容 | 来源主机 | 证据片段路径 | 时间戳 | 状态 | 双通道 |"
SEP = "|---|---|---|---|---|---|---|---|"


def make(text):
    return reg.parse_registry(text)


class ParseValidateTests(unittest.TestCase):
    def test_compliant_registry_passes(self):
        text = "\n".join([
            "# r", "", HEADER, SEP,
            "| L-1 | 凭据 | u:p | 10.0.0.1 | loot/demo.md | 2026-11-15T10:00:00+08:00 | 有效 | — |",
            "", "## 攻击路径", "", "- 入口 10.0.0.1 → 10.0.0.2",
        ])
        with tempfile.TemporaryDirectory() as t:
            os.makedirs(os.path.join(t, "loot"))
            open(os.path.join(t, "loot", "demo.md"), "w").close()
            r = reg.validate(make(text), root=t)
            self.assertTrue(r["passed"], r["blocking"])
            self.assertTrue(all(r["checks"].values()))

    def test_column_order_permutation_still_passes(self):
        perm = "| 类型 | 编号 | 内容 | 来源主机 | 证据片段路径 | 时间戳 | 状态 | 双通道 |"
        text = "\n".join([perm, SEP, "| 凭据 | L-1 | u:p | h | — | t | 有效 | — |",
                          "", "## 攻击路径", "- x"])
        r = reg.validate(make(text), root=".")
        self.assertTrue(r["checks"]["columns"])

    def test_empty_registry_passes_but_require_loot_fails(self):
        r = reg.validate(make(reg.SKELETON), root=".")
        self.assertTrue(r["passed"])
        r2 = reg.validate(make(reg.SKELETON), root=".", require_loot=True)
        self.assertFalse(r2["passed"])
        self.assertIn("空态", " ".join(r2["blocking"]))

    def test_bad_columns_fail(self):
        text = "| 编号 | 类型 |\n|---|---|\n| L-1 | 凭据 |"
        r = reg.validate(make(text), root=".")
        self.assertFalse(r["checks"]["columns"])

    def test_row_cell_count_fail(self):
        text = "\n".join([HEADER, SEP, "| L-1 | 凭据 |", "", "## 攻击路径", "- x"])
        r = reg.validate(make(text), root=".")
        self.assertFalse(r["checks"]["rows"])
        self.assertFalse(r["passed"])

    def test_bad_id_and_duplicate(self):
        rows = [
            "| X-1 | 凭据 | c | h | — | t | 有效 | — |",
            "| L-1 | 凭据 | c | h | — | t | 有效 | — |",
            "| L-1 | 凭据 | c | h | — | t | 有效 | — |",
        ]
        text = "\n".join([HEADER, SEP] + rows + ["", "## 攻击路径", "- x"])
        r = reg.validate(make(text), root=".")
        self.assertFalse(r["checks"]["ids"])
        self.assertIn("编号", " ".join(r["blocking"]))

    def test_evidence_missing_fails(self):
        text = "\n".join([HEADER, SEP,
                          "| L-1 | 凭据 | c | h | loot/nope.md | t | 有效 | — |",
                          "", "## 攻击路径", "- x"])
        r = reg.validate(make(text), root="/nonexistent")
        self.assertFalse(r["checks"]["evidence"])

    def test_status_must_match_type(self):
        text = "\n".join([HEADER, SEP,
                          "| L-1 | 会话 | ssh | h | — | t | 有效 | — |",
                          "", "## 攻击路径", "- x"])
        r = reg.validate(make(text), root=".")
        self.assertFalse(r["checks"]["statuses"])

    def test_flag_dual_channel(self):
        ok = "\n".join([HEADER, SEP,
                        "| L-1 | flag | ai_vector.txt | h | — | t | 已取证 | 面板=F；截图=s.png |",
                        "", "## 攻击路径", "- x"])
        r = reg.validate(make(ok), root=".")
        self.assertTrue(r["checks"]["dual_channel"])
        self.assertEqual(r["flags"][0]["consistent"], True)
        bad = "\n".join([HEADER, SEP,
                         "| L-1 | flag | ai_vector.txt | h | — | t | 已取证 | — |",
                         "", "## 攻击路径", "- x"])
        r2 = reg.validate(make(bad), root=".")
        self.assertFalse(r2["checks"]["dual_channel"])

    def test_attack_path_required_when_rows(self):
        text = "\n".join([HEADER, SEP, "| L-1 | 凭据 | c | h | — | t | 有效 | — |"])
        r = reg.validate(make(text), root=".")
        self.assertFalse(r["checks"]["attack_path"])

    def test_proof_single_warning(self):
        text = "\n".join([HEADER, SEP,
                          "| L-1 | flag | proof.txt | h | — | t | 已取证 | 面板=F；截图=a.png |",
                          "| L-2 | flag | proof.txt | h2 | — | t | 已取证 | 面板=F；截图=b.png |",
                          "", "## 攻击路径", "- x"])
        r = reg.validate(make(text), root=".")
        self.assertTrue(any("proof.txt" in w for w in r["warnings"]))

    def test_parse_dual(self):
        self.assertEqual(reg.parse_dual("面板=F；截图=s.png"), ("F", "s.png"))
        self.assertEqual(reg.parse_dual("—"), ("", ""))

    def test_fragment_pieces(self):
        complete = ("#### 确切命令\n\nx\n\n#### 关键输出\n\ny\n\n"
                    "#### 截图（访问证明）\n\n![](s.png)\n")
        self.assertTrue(reg.fragment_pieces(complete)["complete"])
        incomplete = "#### 确切命令\n\nx\n\n#### 关键输出\n\n（未提供）\n"
        self.assertFalse(reg.fragment_pieces(incomplete)["complete"])


class CliTests(unittest.TestCase):
    def test_init_and_idempotent(self):
        with tempfile.TemporaryDirectory() as t:
            p = os.path.join(t, "loot", "registry.md")
            self.assertEqual(cli.main(["--registry", p, "--root", t, "init"]), 0)
            self.assertTrue(os.path.isfile(p))
            self.assertEqual(cli.main(["--registry", p, "--root", t, "init"]), 2)
            self.assertEqual(cli.main(["--registry", p, "--root", t, "init", "--force"]), 0)

    def test_register_credential_and_validate(self):
        with tempfile.TemporaryDirectory() as t:
            p = os.path.join(t, "loot", "registry.md")
            os.makedirs(os.path.join(t, "loot"))
            open(os.path.join(t, "loot", "demo.md"), "w").close()
            cli.main(["--registry", p, "--root", t, "init"])
            rc = cli.main(["--registry", p, "--root", t, "register", "--type", "凭据",
                           "--content", "u:p", "--host", "10.0.0.1",
                           "--evidence", "loot/demo.md"])
            self.assertEqual(rc, 0)
            cli.main(["--registry", p, "--root", t, "register", "--path", "入口 A → B"])
            self.assertEqual(cli.main(["--registry", p, "--root", t, "validate"]), 0)
            text = open(p, encoding="utf-8").read()
            self.assertIn("| L-1 | 凭据 |", text)

    def test_register_flag_requires_both_channels(self):
        with tempfile.TemporaryDirectory() as t:
            p = os.path.join(t, "loot", "registry.md")
            cli.main(["--registry", p, "--root", t, "init"])
            rc = cli.main(["--registry", p, "--root", t, "register", "--type", "flag",
                           "--content", "ai_vector.txt", "--flag-panel", "F"])
            self.assertEqual(rc, 2)

    def test_register_flag_writes_dual_and_proof_marker(self):
        with tempfile.TemporaryDirectory() as t:
            p = os.path.join(t, "loot", "registry.md")
            cli.main(["--registry", p, "--root", t, "init"])
            cli.main(["--registry", p, "--root", t, "register", "--type", "flag",
                      "--content", "proof.txt", "--host", "dc", "--evidence", "—",
                      "--flag-panel", "F", "--flag-shot", "s.png"])
            text = open(p, encoding="utf-8").read()
            self.assertIn("面板=F", text)
            self.assertIn("截图=s.png", text)
            self.assertIn("仅可提交一次", text)

    def test_validate_missing_registry_exit2(self):
        with tempfile.TemporaryDirectory() as t:
            rc = cli.main(["--registry", os.path.join(t, "none.md"),
                           "--root", t, "validate"])
            self.assertEqual(rc, 2)

    def test_validate_json_shape(self):
        with tempfile.TemporaryDirectory() as t:
            p = os.path.join(t, "loot", "registry.md")
            cli.main(["--registry", p, "--root", t, "init"])
            import contextlib
            import io
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                cli.main(["--registry", p, "--root", t, "validate", "--json"])
            import json
            data = json.loads(buf.getvalue())
            self.assertIn("checks", data)
            self.assertIn("flags", data)
            self.assertTrue(data["passed"])


if __name__ == "__main__":
    unittest.main()
