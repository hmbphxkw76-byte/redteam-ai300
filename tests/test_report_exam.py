#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""report-exam 报告组装器外部行为测试（S2 / 阶段 9）。

以 #111 v2 的 AC-01..AC-15 为判据，只测外部行为（给定证据源 → 报告结构 /
校验结论），不断言实现细节。零外部依赖，本地与 CI 判定一致。

运行：python -m unittest discover -s tests
"""
import os
import re
import sys
import tempfile
import types
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from report_exam import (  # noqa: E402
    Fragment, MemoryEvidenceSource, DirEvidenceSource, build_index,
    parse_fragment, render_skeleton, render_host_section,
    render_all_host_sections, collect_ai_logs, render_bilingual,
    extract_facts, verify_report, render_pdf, make_archive,
    assemble_report, package,
)
from report_exam.bilingual import (  # noqa: E402
    LONG_POC_THRESHOLD, long_poc_fragments, render_appendix_a,
)

EXPECTED = ["chain1-h1", "standalone", "domain-controller"]


def frag(step_id="aia-01", host="h1", **kw):
    base = dict(step_id=step_id, host=host, target="10.0.0.1",
                title="step", command="whoami", output="uid=0(root)",
                screenshot="shots/aia-01.png", ai_log="", flag="",
                raw="", source_path="evidence/demo/aia-01.md")
    base.update(kw)
    return Fragment(**base)


class FakeRunner:
    """注入式外部工具执行器：不真实调用 pandoc/7z，但落盘占位产物。"""

    def __init__(self, fail_on=None):
        self.calls = []
        self.fail_on = fail_on

    def __call__(self, argv, **kwargs):
        self.calls.append(argv)
        if argv[0] == self.fail_on:
            raise OSError("tool not available: %s" % argv[0])
        if argv[0] == "pandoc":
            with open(argv[-1], "wb") as f:
                f.write(b"%PDF-1.4\n")
        elif argv[0] == "7z":
            with open(argv[3], "wb") as f:
                f.write(b"7z-archive")
        return types.SimpleNamespace(returncode=0)


class IndexTests(unittest.TestCase):
    def test_parse_fragment_extracts_all_five_pieces(self):
        text = """### 步骤 aia-07：提权验证

> **目标**：`10.0.0.7`　|　**时间戳**：`2026-11-14T10:00:00+08:00`　|　**证据片段**（collect_evidence.py）

#### 确切命令

```bash
id
```

#### 关键输出

```text
uid=0(root)
```

#### 截图（访问证明）

![aia-07 截图](shots/aia-07.png)

#### AI 交互日志

```text
prompt: bypass guardrail
```

#### flag 取证（双通道一致）

```text
OSAI{proof}
```
"""
        f = parse_fragment(text, source_path="evidence/x/aia-07.md")
        self.assertEqual(f.step_id, "aia-07")
        self.assertEqual(f.title, "提权验证")
        self.assertEqual(f.target, "10.0.0.7")
        self.assertEqual(f.command, "id")
        self.assertEqual(f.output, "uid=0(root)")
        self.assertEqual(f.screenshot, "shots/aia-07.png")
        self.assertEqual(f.ai_log, "prompt: bypass guardrail")
        self.assertEqual(f.flag, "OSAI{proof}")
        self.assertEqual(f.host, "10.0.0.7")

    def test_parse_fragment_missing_fields_are_empty(self):
        f = parse_fragment("### 步骤 aia-00\n\nno blocks here\n")
        self.assertEqual(f.step_id, "aia-00")
        self.assertEqual(f.command, "")
        self.assertEqual(f.screenshot, "")
        self.assertEqual(f.host, "")

    def test_AC01_index_covers_all_expected_hosts_without_duplicates(self):
        src = MemoryEvidenceSource([frag(host="h1"), frag("aia-02", host="h1")])
        m = build_index(src, expected_hosts=EXPECTED)
        self.assertTrue(set(m.hosts) >= set(EXPECTED))
        self.assertEqual(len(m.hosts["h1"]), 2)
        self.assertEqual(m.hosts["standalone"], [])

    def test_dir_evidence_source_reads_multiple_fragments(self):
        with tempfile.TemporaryDirectory() as d:
            with open(os.path.join(d, "a.md"), "w", encoding="utf-8") as f:
                f.write("### 步骤 aia-01\n\n#### 确切命令\n\n```bash\nid\n```\n"
                        "\n### 步骤 aia-02\n\n#### 确切命令\n\n```bash\nwhoami\n```\n")
            src = DirEvidenceSource(d)
            ids = [f.step_id for f in src.iter_fragments()]
            self.assertEqual(ids, ["aia-01", "aia-02"])


class SkeletonTests(unittest.TestCase):
    def test_AC03_four_chapters_and_six_anchors(self):
        m = build_index(MemoryEvidenceSource([frag()]), expected_hosts=EXPECTED)
        t = render_skeleton(m)
        for a in ["## Introduction", "## Objective", "## Requirements",
                  "# Executive Summary", "## High-Level Attack Path",
                  "# Attack Walkthrough", "# Appendix"]:
            with self.subTest(anchor=a):
                self.assertIn(a, t)
        self.assertIn("Target Inventory & Point Allocation", t)

    def test_AC04_toc_entry_and_verbatim_copyright(self):
        t = render_skeleton(build_index(MemoryEvidenceSource([])))
        self.assertIn("Offsec AI Red Teamer Report", t)
        self.assertIn("Copyright © 2026 OffSec Ltd. All rights reserved.", t)

    def test_AC14_two_decoys_confirmed_not_exploitable(self):
        t = render_skeleton(build_index(MemoryEvidenceSource([])))
        self.assertIn("Intentionally Not Vulnerable Hosts", t)
        self.assertEqual(t.count("confirmed not exploitable"), 3)


class SectionTests(unittest.TestCase):
    def test_AC05_five_section_markers(self):
        s = render_host_section("h1", [frag()])
        for a in ["#### Initial Access / Exploitation",
                  "#### Privilege Escalation (if applicable)", "#### Proof"]:
            self.assertIn(a, s)

    def test_AC06_command_and_output_verbatim(self):
        f = frag(command="curl -X POST http://target/api", output="HTTP/1.1 200 OK\nOK")
        s = render_host_section("h1", [f])
        self.assertIn(f.command, s)
        self.assertIn(f.output, s)

    def test_AC15_evidence_attribution_path_present(self):
        s = render_all_host_sections(build_index(MemoryEvidenceSource([frag()])))
        self.assertIn("evidence/demo/aia-01.md", s)
        self.assertIn("Evidence attribution", s)

    def test_AC02_missing_host_recorded_not_fabricated(self):
        m = build_index(MemoryEvidenceSource([]), expected_hosts=EXPECTED)
        s = render_all_host_sections(m)
        self.assertIn("NOT ATTEMPTED", s)
        self.assertNotIn("```bash", s)
        zh = render_all_host_sections(m, lang="zh")
        self.assertIn("未达成", zh)

    def test_en_and_zh_labels_switch_but_values_stay_verbatim(self):
        f = frag(ai_log="prompt: test", flag="OSAI{x}")
        en = render_host_section("h1", [f], lang="en")
        zh = render_host_section("h1", [f], lang="zh")
        self.assertIn("AI Interaction Log", en)
        self.assertIn("AI 交互日志", zh)
        for t in (en, zh):
            self.assertIn(f.command, t)
            self.assertIn(f.flag, t)

    def test_flag_and_privilege_routing(self):
        f = frag(command="id", flag="OSAI{ai_vector}")
        s = render_host_section("h1", [f])
        self.assertIn("Flag Proof (dual-channel)", s)
        self.assertIn("#### Privilege Escalation (if applicable)", s)
        proof_part = s.split("#### Proof", 1)[1]
        self.assertIn(f.output, proof_part)
        self.assertIn(f.flag, proof_part)


class AppendixTests(unittest.TestCase):
    def test_AC07_ai_logs_fully_copied(self):
        fs = [frag("aia-01", ai_log="prompt: one"),
              frag("aia-02", ai_log="prompt: two"), frag("aia-03")]
        a = collect_ai_logs(fs)
        self.assertIn("prompt: one", a)
        self.assertIn("prompt: two", a)
        self.assertIn("## D. AI Session / Prompt History", a)

    def test_no_ai_logs_gives_explicit_placeholder_both_langs(self):
        for lang, marker in (("en", "No AI interaction logs"), ("zh", "未提供 AI 交互日志")):
            self.assertIn(marker, collect_ai_logs([frag()], lang=lang))

    def test_AC11_long_poc_offloaded_to_appendix_a(self):
        long_output = "\n".join("line-%d" % i for i in range(LONG_POC_THRESHOLD + 1))
        m = build_index(MemoryEvidenceSource([frag(output=long_output)]))
        self.assertEqual(len(long_poc_fragments(m)), 1)
        a = render_appendix_a(m)
        self.assertIn("line-60", a)
        self.assertIn("## A. Scripts & PoC", a)

    def test_short_output_not_offloaded(self):
        m = build_index(MemoryEvidenceSource([frag()]))
        a = render_appendix_a(m)
        self.assertIn("No PoC longer than", a)


class BilingualTests(unittest.TestCase):
    def test_AC10_facts_block_identical_between_versions(self):
        m = build_index(MemoryEvidenceSource([frag(flag="OSAI{x}")]),
                        expected_hosts=EXPECTED)
        en, zh = render_bilingual(m)
        self.assertTrue(extract_facts(en))
        self.assertEqual(extract_facts(en), extract_facts(zh))
        self.assertIn("本报告涵盖", zh)

    def test_en_body_has_no_chinese_prose(self):
        m = build_index(MemoryEvidenceSource([frag()]), expected_hosts=EXPECTED)
        en, _ = render_bilingual(m)
        no_comment = re.sub(r"<!--.*?-->", "", en, flags=re.S)
        body = re.sub(r"```.*?```", "", no_comment, flags=re.S)
        self.assertFalse(any(re.search(r"[一-鿿]", l) for l in body.splitlines()),
                         "EN 官方版叙述正文不得含中文（§5）")

    def test_extract_facts_returns_empty_when_block_absent(self):
        self.assertEqual(extract_facts("# nothing"), "")


class VerifyTests(unittest.TestCase):
    def setUp(self):
        self.m = build_index(
            MemoryEvidenceSource([frag(flag="OSAI{ai_vector}", ai_log="prompt: p")]),
            expected_hosts=EXPECTED)
        self.en, _ = render_bilingual(self.m)
        self.app = collect_ai_logs([f for fs in self.m.hosts.values() for f in fs])

    def test_AC08_AC13_eight_checks_all_green(self):
        v = verify_report(self.m, self.en, appendix_md=self.app)
        self.assertTrue(v["passed"], "blocking=%s" % v["blocking"])
        self.assertEqual(len(v["checks"]), 9)  # vrf-01..08 + proof-single
        self.assertTrue(all(v["checks"].values()))

    def test_AC09_duplicate_proof_submission_blocks(self):
        fs = [frag("aia-01", flag="proof.txt: OSAI{1}"),
              frag("aia-02", flag="proof.txt: OSAI{2}")]
        m = build_index(MemoryEvidenceSource(fs))
        en, _ = render_bilingual(m)
        v = verify_report(m, en, appendix_md=en)
        self.assertFalse(v["checks"]["proof-single"])
        self.assertFalse(v["passed"])
        self.assertTrue(any("proof.txt" in b for b in v["blocking"]))

    def test_missing_ai_log_in_appendix_blocks(self):
        v = verify_report(self.m, self.en, appendix_md="(empty appendix)")
        self.assertFalse(v["checks"]["vrf-05"])
        self.assertFalse(v["passed"])

    def test_missing_anchor_blocks(self):
        v = verify_report(self.m, "# truncated report")
        self.assertFalse(v["checks"]["vrf-06"])
        self.assertFalse(v["passed"])

    def test_uncaptured_flag_is_missing_not_blocking(self):
        m = build_index(MemoryEvidenceSource([frag()]), expected_hosts=EXPECTED)
        en, _ = render_bilingual(m)
        v = verify_report(m, en, appendix_md=en)
        self.assertTrue(v["passed"])
        self.assertTrue(any("vrf-04" in x for x in v["missing"]))

    def test_banned_glossary_terms_detected(self):
        v = verify_report(self.m, self.en + "\n蜜罐\n", appendix_md=self.app)
        self.assertFalse(v["checks"]["vrf-08"])


class PackagingTests(unittest.TestCase):
    def test_AC12_naming_and_size_rules(self):
        from report_exam.package import check_naming_and_size, MAX_ARCHIVE_BYTES
        with tempfile.TemporaryDirectory() as d:
            pdf = os.path.join(d, "OSAI-OS-12345-Exam-Report.pdf")
            z = os.path.join(d, "OSAI-OS-12345-Exam-Report.7z")
            open(pdf, "wb").close()
            with open(z, "wb") as f:
                f.truncate(MAX_ARCHIVE_BYTES + 1)
            ok, miss = check_naming_and_size(pdf, z, "12345")
            self.assertFalse(ok)
            self.assertTrue(any("100MB" in x for x in miss))
            ok2, miss2 = check_naming_and_size("wrong.pdf", z, "12345")
            self.assertFalse(ok2)
            self.assertTrue(any("PDF 命名" in x for x in miss2))

    def test_render_pdf_and_archive_use_toc_and_no_password(self):
        with tempfile.TemporaryDirectory() as d:
            r = FakeRunner()
            pdf = render_pdf("# report", d, "12345", runner=r)
            z = make_archive(pdf, d, "12345", runner=r)
            self.assertIn("--toc", r.calls[0])
            self.assertNotIn("-p", r.calls[1])
            self.assertTrue(os.path.isfile(z))

    def test_missing_tool_raises_runtime_error_VG3(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(RuntimeError):
                render_pdf("# x", d, "12345", runner=FakeRunner(fail_on="pandoc"))
            with self.assertRaises(RuntimeError):
                make_archive("x.pdf", d, "12345", runner=FakeRunner(fail_on="7z"))

    def test_package_success_with_injected_runner(self):
        m = build_index(MemoryEvidenceSource([frag(flag="OSAI{x}", ai_log="p")]),
                        expected_hosts=EXPECTED)
        en, _ = render_bilingual(m)
        with tempfile.TemporaryDirectory() as d:
            res = package(m, en, d, runner=FakeRunner())
            self.assertTrue(res["passed"], "blocking=%s" % res["blocking"])
            self.assertTrue(res["verify"]["checks"]["vrf-07"])

    def test_package_records_vg3_when_tool_missing(self):
        m = build_index(MemoryEvidenceSource([frag()]), expected_hosts=EXPECTED)
        en, _ = render_bilingual(m)
        with tempfile.TemporaryDirectory() as d:
            res = package(m, en, d, runner=FakeRunner(fail_on="pandoc"))
            self.assertTrue(res["vg3"])
            self.assertFalse(res["passed"])


class AssembleTests(unittest.TestCase):
    def test_all_AC_pass_except_packaging_when_skipped(self):
        src = MemoryEvidenceSource([frag(flag="OSAI{x}", ai_log="prompt: p")])
        r = assemble_report(src, expected_hosts=EXPECTED, do_package=False)
        self.assertTrue(r["all_ac_pass"] or not r["ac"]["AC-12"])
        for k, v in r["ac"].items():
            with self.subTest(ac=k):
                self.assertIn(k, r["ac"])
        self.assertTrue(r["ac"]["AC-06"])
        self.assertTrue(r["ac"]["AC-10"])
        self.assertTrue(r["verify"]["passed"])

    def test_full_pipeline_with_packaging(self):
        src = MemoryEvidenceSource([frag(flag="OSAI{x}", ai_log="prompt: p")])
        with tempfile.TemporaryDirectory() as d:
            r = assemble_report(src, expected_hosts=EXPECTED, osid="12345",
                                out_dir=d, runner=FakeRunner())
            self.assertTrue(r["all_ac_pass"], str(r["ac"]))
            self.assertIsNotNone(r["package"]["pdf"])

    def test_cli_index_and_build(self):
        from report_exam.__main__ import main
        with tempfile.TemporaryDirectory() as d:
            ev = os.path.join(d, "ev")
            os.makedirs(ev)
            with open(os.path.join(ev, "a.md"), "w", encoding="utf-8") as f:
                f.write("### 步骤 aia-01\n\n#### 确切命令\n\n```bash\nid\n```\n")
            idx = os.path.join(d, "index.json")
            self.assertEqual(main(["index", "--evidence-dir", ev, "--out", idx]), 0)
            outdir = os.path.join(d, "report")
            self.assertEqual(main(["build", "--evidence-dir", ev,
                                   "--out-dir", outdir, "--no-package"]), 0)
            self.assertTrue(os.path.isfile(os.path.join(outdir, "report-EN.md")))


if __name__ == "__main__":
    unittest.main()
