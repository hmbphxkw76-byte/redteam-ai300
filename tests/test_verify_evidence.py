"""verify-evidence 机读校验器自测（T07 / CI S2）。

四类夹具：合规 / 缺面板 flag / 重复 proof.txt / 缺章节，外加 dry-run、
命名体积、AI 日志附录、术语证据区间豁免与 CLI 退出码。标准库 unittest，零依赖。
"""
import contextlib
import importlib.util
import io
import json
import os
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_spec = importlib.util.spec_from_file_location(
    "verify_evidence_shared", os.path.join(ROOT, "tools", "verify_evidence.py"))
VE = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(VE)

COPYRIGHT = "Copyright © 2026 OffSec Ltd. All rights reserved."
ANCHORS = VE.REQUIRED_ANCHORS


def report_text():
    inventory = " / ".join(VE.SCORED_TARGETS)  # 8 个计分目标键（§2.2）
    return "\n\n".join([
        "# OSID: 12345", COPYRIGHT, "# Offsec AI Red Teamer Report",
        "## Introduction", "## Objective", "## Requirements",
        "# Executive Summary", "## High-Level Attack Path",
        "## Target Inventory & Point Allocation", inventory,
        "# Attack Walkthrough", "# Appendix",
    ])


def frag(step="aia-01", host="standalone", flag="", ai_log="", **kw):
    base = dict(step_id=step, host=host, command="id", output="uid=0(root)",
                screenshot="shots/aia-01.png", ai_log=ai_log, flag=flag)
    base.update(kw)
    return base


def payload(report=None, appendix="", frags=None, panel=None, pdf=None, zip_path=None,
            **extra):
    body = {
        "report_md": report_text() if report is None else report,
        "appendix_md": appendix,
        "osid": "12345",
        "fragments": [] if frags is None else frags,
        "panel_flags": {} if panel is None else panel,
        "pdf_path": pdf,
        "zip_path": zip_path,
    }
    body.update(extra)
    return body


class VerifyEvidenceTests(unittest.TestCase):

    def _artifacts(self, d):
        pdf = os.path.join(d, "OSAI-OS-12345-Exam-Report.pdf")
        arc = os.path.join(d, "OSAI-OS-12345-Exam-Report.7z")
        with open(pdf, "wb") as f:
            f.write(b"%PDF-1.7\n")
        with open(arc, "wb") as f:
            f.write(b"7z-archive")
        return pdf, arc

    def test_compliant_payload_all_eight_checks_pass(self):
        with tempfile.TemporaryDirectory() as d:
            pdf, arc = self._artifacts(d)
            p = payload(appendix="prompt: p\n",
                        frags=[frag(flag="OSAI{x}", ai_log="prompt: p")],
                        panel={"standalone": "OSAI{x}"}, pdf=pdf, zip_path=arc)
            r = VE.verify(p, require_artifacts=True)
            for k in ["vrf-01", "vrf-02", "vrf-03", "vrf-04", "vrf-05",
                      "vrf-06", "vrf-07", "vrf-08", "proof-single"]:
                with self.subTest(check=k):
                    self.assertIs(r["checks"][k], True)
            self.assertTrue(r["passed"], str(r["blocking"]))
            self.assertTrue(r["submission_ready"])
            self.assertEqual(r["pending"], [])

    def test_missing_panel_flag_is_blocking(self):
        p = payload(frags=[frag(flag="OSAI{x}")], panel={})
        r = VE.verify(p, require_artifacts=False)
        self.assertIs(r["checks"]["vrf-04"], False)
        self.assertTrue(any("vrf-04" in b for b in r["blocking"]))
        self.assertFalse(r["passed"])

    def test_duplicate_proof_txt_is_blocking(self):
        # v2 AC-14：单次约束按目标键（domain-controller）判定，夹具随之对齐
        p = payload(frags=[frag("aia-01", host=VE.DC_KEY, flag="OSAI{dcmarker}"),
                           frag("aia-02", host=VE.DC_KEY, flag="OSAI{dcmarker}")])
        r = VE.verify(p, require_artifacts=False)
        self.assertIs(r["checks"]["proof-single"], False)
        self.assertTrue(any("proof.txt 提交记录 2 次" in b for b in r["blocking"]))

    def test_flag_substring_does_not_count_as_proof_submission(self):
        # AC-14 反例：非域控主机且 flag 值含 proof.txt 子串，不构成提交记录
        p = payload(frags=[frag("aia-01", host="standalone",
                                flag="OSAI{proof.txt-decoy}")],
                    panel={"standalone": "OSAI{proof.txt-decoy}"})
        r = VE.verify(p, require_artifacts=False)
        self.assertIs(r["checks"]["proof-single"], True)

    def test_missing_anchors_is_blocking(self):
        p = payload(report="# OSID: 12345\n\n" + COPYRIGHT)
        r = VE.verify(p, require_artifacts=False)
        self.assertIs(r["checks"]["vrf-06"], False)
        self.assertTrue(any("vrf-06" in b for b in r["blocking"]))

    def test_dry_run_records_VG3_and_never_marks_submission_ready(self):
        r = VE.verify(payload(), require_artifacts=False)
        self.assertIsNone(r["checks"]["vrf-07"])
        self.assertTrue(any("VG-3" in x for x in r["pending"]))
        self.assertFalse(r["submission_ready"])
        self.assertTrue(r["passed"])  # 核实闸是 pending，不是 blocking

    def test_ai_log_must_appear_verbatim_in_appendix(self):
        p = payload(frags=[frag(ai_log="prompt: p")], appendix="(empty)")
        r = VE.verify(p, require_artifacts=False)
        self.assertIs(r["checks"]["vrf-05"], False)
        self.assertTrue(any("vrf-05" in b for b in r["blocking"]))

    def test_naming_and_size_rules(self):
        with tempfile.TemporaryDirectory() as d:
            pdf, arc = self._artifacts(d)
            self.assertTrue(VE.check_naming_and_size(pdf, arc, "12345")[0])
            ok, miss = VE.check_naming_and_size("wrong.pdf", arc, "12345")
            self.assertFalse(ok)
            self.assertTrue(any("PDF 命名" in m for m in miss))
            ok, miss = VE.check_naming_and_size(pdf, None, "12345")
            self.assertFalse(ok)
            self.assertTrue(any("归档产物缺失" in m for m in miss))
            with open(arc, "wb") as f:
                f.truncate(VE.MAX_ARCHIVE_BYTES + 1)
            ok, miss = VE.check_naming_and_size(pdf, arc, "12345")
            self.assertFalse(ok)
            self.assertTrue(any("100MB" in m for m in miss))

    def test_three_piece_gap_is_recorded_not_blocking(self):
        p = payload(frags=[frag(screenshot="")])
        r = VE.verify(p, require_artifacts=False)
        self.assertTrue(any("vrf-03" in m for m in r["missing"]))
        self.assertTrue(r["passed"])  # SKILL §9：未取分缺失属预期

    def test_obsolete_term_blocked_but_verbatim_evidence_exempt(self):
        terms = VE.load_avoid_terms()
        self.assertTrue(terms)
        bad = terms[0]
        base = report_text()
        r_bad = VE.verify(payload(report=base + "\n" + bad), require_artifacts=False)
        self.assertIs(r_bad["checks"]["vrf-08"], False)
        wrapped = (base + "\n<!-- EVIDENCE-FRAGMENT-START -->\n" + bad
                   + "\n<!-- EVIDENCE-FRAGMENT-END -->")
        r_ok = VE.verify(payload(report=wrapped), require_artifacts=False)
        self.assertIs(r_ok["checks"]["vrf-08"], True)

    def test_cli_exit_codes(self):
        with tempfile.TemporaryDirectory() as d:
            pdf, arc = self._artifacts(d)
            good = payload(pdf=pdf, zip_path=arc)
            bad = payload(report="# OSID: 12345")
            gp = os.path.join(d, "good.json")
            bp = os.path.join(d, "bad.json")
            for path, obj in ((gp, good), (bp, bad)):
                with open(path, "w", encoding="utf-8") as f:
                    json.dump(obj, f)
            with contextlib.redirect_stdout(io.StringIO()), \
                    contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(VE.main(["--payload", gp]), 0)
                self.assertEqual(VE.main(["--payload", bp]), 1)
                self.assertEqual(VE.main(["--payload", os.path.join(d, "nope.json")]), 2)


class FakeTools(VE.Toolchain):
    """S-3 替身：技能校验结论 / 术语表 / 文件 stat 可编程。"""

    def __init__(self, skill_errors=None, avoid=None, sizes=None,
                 absent=(), encrypted=None, avoid_none=False, skills=None):
        self.skill_errors = list(skill_errors or [])
        self._avoid = ["旧称"] if avoid is None else list(avoid)
        self._avoid_none = avoid_none
        self._sizes = dict(sizes or {})
        self._absent = set(absent or ())
        self._encrypted = encrypted
        self._skills = skills if skills is not None else [
            ("attack-ai-agent", "P0", "AI向量机"), ("attack-embeddings", "P1", "AI向量机")]
        self.skill_calls = 0

    def validate_skills(self, skills_dir=None):
        self.skill_calls += 1
        return list(self.skill_errors)

    def skill_meta(self, skills_dir=None):
        return list(self._skills)

    def avoid_terms(self, glossary_path=VE.DEFAULT_GLOSSARY):
        return None if self._avoid_none else list(self._avoid)

    def stat(self, path):
        if path in self._absent:
            return False, 0
        if path in self._sizes:
            return True, self._sizes[path]
        return True, 1024

    def archive_encrypted(self, path):
        return self._encrypted


def good_points():
    return {"chain1-host1": 15, "chain1-host2": 15, "chain1-host3": 15,
            "chain2-host1": 15, "chain2-host2": 10, "chain2-host3": 10,
            "standalone": 15, "domain-controller": 5}


FRAGMENT_MD = """### 步骤 aia-01：读取 flag

**目标**：`10.0.0.1`

#### 确切命令

```bash
cat /root/ai_vector.txt
```

#### 关键输出

```text
OSAI{demo-flag}
```

#### 截图（访问证明）

![aia-01](shots/aia-01.png)

```text
root@target:~# id
uid=0(root) gid=0(root) groups=0(root)
root@target:~# cat /root/ai_vector.txt
OSAI{demo-flag}
```
"""


def dual_fragment(panel="OSAI{demo-flag}", shot="OSAI{demo-flag}",
                  host="standalone"):
    """按 `tools/collect_evidence.py` 写出端格式构造含双通道明细表的片段。"""
    table = ("\n#### flag 取证（双通道一致）\n\n"
             "```text\n%s\n```\n\n"
             "| 通道 | 值 |\n|---|---|\n"
             "| 控制面板提交值 | %s |\n"
             "| 截图/正文中的值 | %s |\n"
             "| 一致性 | **%s** |\n"
             % (panel or shot,
                ("`%s`" % panel) if panel else "（缺失）",
                ("`%s`" % shot) if shot else "（缺失）",
                "一致" if panel == shot else "不一致"))
    return FRAGMENT_MD.replace("**目标**：`10.0.0.1`",
                              "**目标**：`%s`" % host) + table


class VerifyEvidenceV2Tests(unittest.TestCase):
    """v2 AC-01…AC-20 的验收用例（每条 AC 至少一个用例）。"""

    # --- AC-01 两种入口等价 -------------------------------------------------
    def test_AC01_payload_and_loot_entries_agree(self):
        with tempfile.TemporaryDirectory() as d:
            ev = os.path.join(d, "aia-01.md")
            with open(ev, "w", encoding="utf-8") as f:
                f.write(FRAGMENT_MD)
            reg = os.path.join(d, "registry.md")
            with open(reg, "w", encoding="utf-8") as f:
                f.write(
                    "| 编号 | 类型 | 内容 | 来源主机 | 证据片段路径 | 时间戳 | 状态 | 双通道 |\n"
                    "|---|---|---|---|---|---|---|---|\n"
                    "| loot-01 | flag | ai_vector | standalone | aia-01.md | t | valid "
                    "| 面板=OSAI{demo-flag}；截图=shots/aia-01.png |\n\n"
                    "## 攻击路径\n\n- chain1: demo\n")
            tools = FakeTools()
            from_loot_res = VE.verify(VE.from_loot(
                reg, d, report_md=report_text(), appendix_md="prompt: p",
                target_points=good_points()), tools=tools)
            manual = VE.verify(payload(
                appendix="prompt: p", target_points=good_points(),
                frags=[dict(frag("aia-01", host="standalone",
                                 flag="OSAI{demo-flag}", raw=FRAGMENT_MD),
                            pieces={"command": True, "output": True,
                                    "screenshot": True})],
                panel={"standalone": "OSAI{demo-flag}"}), tools=FakeTools())
            self.assertEqual(from_loot_res["checks"], manual["checks"])
            self.assertEqual(from_loot_res["submission_ready"],
                             manual["submission_ready"])
            # 只给登记簿、不给报告 → 报告侧判据必然阻断（入口不缺省放行）
            bare = VE.verify(VE.from_loot(reg, d), tools=FakeTools())
            self.assertIs(bare["checks"]["vrf-06"], False)
            self.assertFalse(bare["passed"])

    def test_AC01b_fragments_dir_entry(self):
        """US-03：直接读一批 collect_evidence 片段，主机按 `**目标**` 归属。"""
        with tempfile.TemporaryDirectory() as d:
            fp = os.path.join(d, "aia-01.md")
            with open(fp, "w", encoding="utf-8") as f:
                f.write(FRAGMENT_MD.replace("**目标**：`10.0.0.1`",
                                            "**目标**：`standalone`")
                        + "\n#### flag 取证（双通道一致）\n\nOSAI{demo-flag}\n")
            res = VE.verify(VE.from_fragments(
                d, report_md=report_text(),
                panel_flags={"standalone": "OSAI{demo-flag}"}), tools=FakeTools())
            self.assertIs(res["checks"]["vrf-03"], True)
            self.assertIs(res["checks"]["vrf-04"], True)
            self.assertEqual(res["checks"]["vrf-01"], True)
            with self.assertRaises(ValueError):
                VE.from_fragments(os.path.join(d, "nope"))

    def test_AC01c_fragments_dir_reads_dual_channel_table(self):
        """无外部 panel_flags 时，片段自带双通道表须支撑 vrf-04（SKILL 执行入口）。"""
        with tempfile.TemporaryDirectory() as d:
            with open(os.path.join(d, "aia-01.md"), "w", encoding="utf-8") as f:
                f.write(dual_fragment())
            inp = VE.from_fragments(d, report_md=report_text())
            self.assertEqual(inp["panel_flags"], {"standalone": "OSAI{demo-flag}"})
            self.assertEqual(inp["fragments"][0]["flag"], "OSAI{demo-flag}")
            res = VE.verify(inp, require_artifacts=False, tools=FakeTools())
            self.assertIs(res["checks"]["vrf-04"], True)
            self.assertTrue(res["passed"], str(res["blocking"]))

    def test_AC01d_fragments_dir_dual_mismatch_blocks(self):
        """面板值 != 截图/正文值 → 失分条款阻断，不得因同入口而放行。"""
        with tempfile.TemporaryDirectory() as d:
            with open(os.path.join(d, "aia-01.md"), "w", encoding="utf-8") as f:
                f.write(dual_fragment(panel="OSAI{panel}", shot="OSAI{shot}"))
            inp = VE.from_fragments(d, report_md=report_text())
            self.assertEqual(inp["panel_flags"]["standalone"], "OSAI{panel}")
            self.assertEqual(inp["fragments"][0]["flag"], "OSAI{shot}")
            res = VE.verify(inp, require_artifacts=False, tools=FakeTools())
            self.assertIs(res["checks"]["vrf-04"], False)
            self.assertTrue(any("面板值" in b for b in res["blocking"]))

    def test_AC01e_fragments_dir_incomplete_channel_blocks(self):
        """任一通道缺失即不登记面板值，由 vrf-04 报缺面板（§2.4）。"""
        with tempfile.TemporaryDirectory() as d:
            with open(os.path.join(d, "aia-01.md"), "w", encoding="utf-8") as f:
                f.write(dual_fragment(shot=""))
            inp = VE.from_fragments(d, report_md=report_text())
            self.assertEqual(inp["panel_flags"], {})
            res = VE.verify(inp, require_artifacts=False, tools=FakeTools())
            self.assertIs(res["checks"]["vrf-04"], False)
            self.assertTrue(any("缺控制面板提交值" in b for b in res["blocking"]))

    def test_AC01f_explicit_panel_flags_take_precedence(self):
        """显式注入优先于片段归一；注入不一致值时仍须阻断。"""
        with tempfile.TemporaryDirectory() as d:
            with open(os.path.join(d, "aia-01.md"), "w", encoding="utf-8") as f:
                f.write(dual_fragment())
            inp = VE.from_fragments(d, report_md=report_text(),
                                    panel_flags={"standalone": "OSAI{override}"})
            self.assertEqual(inp["panel_flags"]["standalone"], "OSAI{override}")
            res = VE.verify(inp, require_artifacts=False, tools=FakeTools())
            self.assertIs(res["checks"]["vrf-04"], False)

    def test_AC21_loot_panel_vs_report_flag_mismatch_blocks(self):
        """#225 J-1：登记簿面板值与报告侧 flag 不一致须阻断，不得自比放行。"""
        with tempfile.TemporaryDirectory() as d:
            text = dual_fragment(panel="OSAI{panel}", shot="OSAI{report}")
            with open(os.path.join(d, "aia-01.md"), "w", encoding="utf-8") as f:
                f.write(text.replace("OSAI{demo-flag}", "OSAI{report}"))
            reg = os.path.join(d, "registry.md")
            with open(reg, "w", encoding="utf-8") as f:
                f.write("| 编号 | 类型 | 内容 | 来源主机 | 证据片段路径 | 时间戳 | 状态 | 双通道 |\n"
                        "|---|---|---|---|---|---|---|---|\n"
                        "| loot-01 | flag | ai_vector | standalone | aia-01.md | t | 已取证 "
                        "| 面板=OSAI{panel}；截图=shots/aia-01.png |\n")
            inp = VE.from_loot(reg, d, report_md=report_text())
            self.assertEqual(inp["panel_flags"]["standalone"], "OSAI{panel}")
            self.assertEqual(inp["fragments"][0]["flag"], "OSAI{report}")
            res = VE.verify(inp, require_artifacts=False, tools=FakeTools())
            self.assertIs(res["checks"]["vrf-04"], False)
            self.assertTrue(any("面板值" in b for b in res["blocking"]))

    def test_AC22_invalidated_status_is_not_scored(self):
        """#225 J-2：登记簿状态「失效」不计已取分，按未取分豁免记录不阻断。"""
        with tempfile.TemporaryDirectory() as d:
            with open(os.path.join(d, "aia-01.md"), "w", encoding="utf-8") as f:
                f.write(dual_fragment())
            reg = os.path.join(d, "registry.md")
            with open(reg, "w", encoding="utf-8") as f:
                f.write("| 编号 | 类型 | 内容 | 来源主机 | 证据片段路径 | 时间戳 | 状态 | 双通道 |\n"
                        "|---|---|---|---|---|---|---|---|\n"
                        "| loot-01 | flag | ai_vector | standalone | aia-01.md | t | 失效 "
                        "| 面板=OSAI{demo-flag}；截图=shots/aia-01.png |\n")
            inp = VE.from_loot(reg, d, report_md=report_text())
            self.assertIs(inp["fragments"][0]["taken"], False)
            res = VE.verify(inp, require_artifacts=False, tools=FakeTools())
            self.assertIs(res["checks"]["vrf-04"], True)
            self.assertTrue(res["passed"], str(res["blocking"]))
            self.assertTrue(any("无 flag 双通道证据" in m for m in res["missing"]))

    def test_AC01g_fragments_dir_cli_entry_passes(self):
        """SKILL 文档入口 `python tools/verify_evidence.py --fragments-dir` 真跑可过。"""
        import subprocess
        with tempfile.TemporaryDirectory() as d:
            with open(os.path.join(d, "aia-01.md"), "w", encoding="utf-8") as f:
                f.write(dual_fragment())
            rep, app = os.path.join(d, "r.txt"), os.path.join(d, "a.txt")
            with open(rep, "w", encoding="utf-8") as f:
                f.write(report_text())
            with open(app, "w", encoding="utf-8") as f:
                f.write("")
            proc = subprocess.run(
                [sys.executable, "tools/verify_evidence.py", "--fragments-dir", d,
                 "--report", rep, "--appendix", app, "--no-artifacts"],
                cwd=ROOT, capture_output=True, text=True)
            self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
            self.assertTrue(json.loads(proc.stdout)["passed"])

    # --- AC-02 用法错误 ----------------------------------------------------
    def test_AC02_usage_errors_exit_2(self):
        with tempfile.TemporaryDirectory() as d:
            bad = os.path.join(d, "bad.json")
            with open(bad, "w", encoding="utf-8") as f:
                f.write("{not json")
            with contextlib.redirect_stdout(io.StringIO()), \
                    contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(VE.main(["--from-loot", os.path.join(d, "none.md")]), 2)
                self.assertEqual(VE.main(["--payload", bad]), 2)
            with self.assertRaises(ValueError):
                VE.load_payload(bad)

    # --- AC-03 技能终检 ----------------------------------------------------
    def test_AC03_skill_validation_gate(self):
        r_bad = VE.verify(payload(), tools=FakeTools(skill_errors=["x: 缺字段"]))
        self.assertIs(r_bad["checks"]["vrf-01"], False)
        self.assertTrue(any("vrf-01" in b for b in r_bad["blocking"]))
        r_ok = VE.verify(payload(), tools=FakeTools())
        self.assertIs(r_ok["checks"]["vrf-01"], True)

    # --- AC-04 计分清单 ----------------------------------------------------
    def test_AC04_point_allocation_matrix(self):
        base = payload()
        self.assertIs(VE.verify(dict(base, target_points=good_points()),
                                tools=FakeTools())["checks"]["vrf-02"], True)
        missing = good_points()
        missing.pop("standalone")
        r = VE.verify(dict(base, target_points=missing), tools=FakeTools())
        self.assertIs(r["checks"]["vrf-02"], False)
        self.assertTrue(any("standalone" in b for b in r["blocking"]))
        wrong = dict(good_points(), standalone=10)
        r2 = VE.verify(dict(base, target_points=wrong), tools=FakeTools())
        self.assertIs(r2["checks"]["vrf-02"], False)
        self.assertTrue(any("分值口径" in b for b in r2["blocking"]))
        r3 = VE.verify(base, tools=FakeTools())
        self.assertIs(r3["checks"]["vrf-02"], True)
        self.assertTrue(any("NOTE-6" in m for m in r3["missing"]))
        p2 = VE.verify(payload(), tools=FakeTools(
            skills=[("attack-fake", "P2", "AI向量机")]))
        self.assertIs(p2["checks"]["vrf-02"], False)
        self.assertTrue(any("高杠杆" in b for b in p2["blocking"]))
        no_keys = report_text().replace("chain1-host1", "")
        r4 = VE.verify(payload(report=no_keys), tools=FakeTools())
        self.assertIs(r4["checks"]["vrf-02"], False)
        self.assertTrue(any("chain1-host1" in b for b in r4["blocking"]))

    # --- AC-05 已取分三件套 ------------------------------------------------
    def test_AC05_scored_fragment_gap_blocks(self):
        r = VE.verify(payload(frags=[frag(flag="OSAI{x}", screenshot="")],
                              panel={"standalone": "OSAI{x}"}), tools=FakeTools())
        self.assertIs(r["checks"]["vrf-03"], False)
        self.assertFalse(r["passed"])

    # --- AC-06 双通道 ------------------------------------------------------
    def test_AC06_dual_channel_match_and_mismatch(self):
        ok = VE.verify(payload(frags=[frag(flag="OSAI{x}")],
                               panel={"standalone": "OSAI{x}"}), tools=FakeTools())
        self.assertIs(ok["checks"]["vrf-04"], True)
        bad = VE.verify(payload(frags=[frag(flag="OSAI{x}")],
                                panel={"standalone": "OSAI{y}"}), tools=FakeTools())
        self.assertIs(bad["checks"]["vrf-04"], False)

    # --- AC-07 访问证明 ----------------------------------------------------
    def test_AC07_access_proof_same_screen(self):
        good = VE.verify(payload(
            frags=[frag(flag="OSAI{demo-flag}", raw=FRAGMENT_MD)],
            panel={"standalone": "OSAI{demo-flag}"}), tools=FakeTools())
        self.assertIs(good["checks"]["vrf-04"], True)
        no_token = FRAGMENT_MD.replace("root@target:~# id\n", "")
        bad = VE.verify(payload(
            frags=[frag(flag="OSAI{demo-flag}", raw=no_token)],
            panel={"standalone": "OSAI{demo-flag}"}), tools=FakeTools())
        self.assertIs(bad["checks"]["vrf-04"], False)
        self.assertTrue(any("访问证明" in b for b in bad["blocking"]))
        # 命令块写了 whoami/id 但截图节无内联文本 → 不构成同屏证据
        cmd_only = FRAGMENT_MD.replace("cat /root/ai_vector.txt", "id && cat /root/ai_vector.txt")
        cmd_only = cmd_only[:cmd_only.index("#### 截图（访问证明）")] + \
            "#### 截图（访问证明）\n\n![aia-01](shots/aia-01.png)\n"
        image_only = VE.verify(payload(
            frags=[frag(flag="OSAI{demo-flag}", raw=cmd_only)],
            panel={"standalone": "OSAI{demo-flag}"}), tools=FakeTools())
        self.assertTrue(any("NOTE-7" in m for m in image_only["missing"]))
        legacy = VE.verify(payload(frags=[frag(flag="OSAI{x}")],
                                   panel={"standalone": "OSAI{x}"}), tools=FakeTools())
        self.assertTrue(any("NOTE-7" in m for m in legacy["missing"]))

    # --- AC-08 AI 日志 -----------------------------------------------------
    def test_AC08_ai_log_verbatim(self):
        r = VE.verify(payload(frags=[frag(ai_log="prompt: p")], appendix_md="x"),
                      tools=FakeTools())
        self.assertIs(r["checks"]["vrf-05"], False)
        r2 = VE.verify(payload(frags=[frag(ai_log="prompt: p")],
                               appendix_md="prompt: p"), tools=FakeTools())
        self.assertIs(r2["checks"]["vrf-05"], True)
        self.assertTrue(any("NOTE-9" in m for m in r2["missing"]))

    # --- AC-09 结构锚点 ----------------------------------------------------
    def test_AC09_each_anchor_required(self):
        for anchor in VE.REQUIRED_ANCHORS:
            with self.subTest(anchor=anchor):
                text = report_text().replace(anchor, "")
                r = VE.verify(payload(report=text), tools=FakeTools())
                self.assertIs(r["checks"]["vrf-06"], False)
                self.assertTrue(any(anchor in b for b in r["blocking"]))

    def test_AC09_host_five_sections_flagged_for_manual_check(self):
        r = VE.verify(payload(frags=[frag()]), tools=FakeTools())
        self.assertTrue(any("NOTE-10" in m for m in r["missing"]))

    # --- AC-10 命名与体积 --------------------------------------------------
    def test_AC10_naming_size_and_missing_artifacts(self):
        with tempfile.TemporaryDirectory() as d:
            pdf, arc = self._artifacts(d)
            ok = VE.verify(payload(pdf=pdf, zip_path=arc), tools=FakeTools())
            self.assertIs(ok["checks"]["vrf-07"], True)
            bad = VE.verify(payload(pdf=os.path.join(d, "wrong.pdf"),
                                    zip_path=arc), tools=FakeTools())
            self.assertIs(bad["checks"]["vrf-07"], False)
            gone = VE.verify(payload(pdf=pdf, zip_path=arc),
                             tools=FakeTools(absent={pdf}))
            self.assertIs(gone["checks"]["vrf-07"], False)
            enc = VE.verify(payload(pdf=pdf, zip_path=arc),
                            tools=FakeTools(encrypted=True))
            self.assertIs(enc["checks"]["vrf-07"], False)
            self.assertTrue(any("密码" in b for b in enc["blocking"]))
            unknown = VE.verify(payload(pdf=pdf, zip_path=arc),
                                tools=FakeTools(encrypted=None))
            self.assertTrue(any("NOTE-8" in m for m in unknown["missing"]))
            huge = VE.verify(payload(pdf=pdf, zip_path=arc),
                             tools=FakeTools(sizes={arc: VE.MAX_ARCHIVE_BYTES + 1}))
            self.assertIs(huge["checks"]["vrf-07"], False)

    def _artifacts(self, d):
        pdf = os.path.join(d, "OSAI-OS-12345-Exam-Report.pdf")
        arc = os.path.join(d, "OSAI-OS-12345-Exam-Report.7z")
        for p, data in ((pdf, b"%PDF-1.7\n"), (arc, b"7z-archive")):
            with open(p, "wb") as f:
                f.write(data)
        return pdf, arc

    # --- AC-11 24h 窗口 ----------------------------------------------------
    def test_AC11_submission_window(self):
        with tempfile.TemporaryDirectory() as d:
            pdf, arc = self._artifacts(d)
            inside = VE.verify(payload(pdf=pdf, zip_path=arc,
                                       exam_end_at="2026-11-14T10:00:00+08:00",
                                       submit_at="2026-11-15T09:00:00+08:00"),
                               tools=FakeTools())
            self.assertIs(inside["checks"]["vrf-07"], True)
            late = VE.verify(payload(pdf=pdf, zip_path=arc,
                                     exam_end_at="2026-11-14T10:00:00+08:00",
                                     submit_at="2026-11-15T11:00:00+08:00"),
                             tools=FakeTools())
            self.assertIs(late["checks"]["vrf-07"], False)
            self.assertTrue(any("24h" in b for b in late["blocking"]))
            unknown = VE.verify(payload(pdf=pdf, zip_path=arc), tools=FakeTools())
            self.assertTrue(any("NOTE-5" in m for m in unknown["missing"]))

    # --- AC-12 dry-run ----------------------------------------------------
    def test_AC12_dry_run_semantics(self):
        r = VE.verify(payload(), require_artifacts=False, tools=FakeTools())
        self.assertIsNone(r["checks"]["vrf-07"])
        self.assertIn("VG-3", " ".join(r["pending"]))
        self.assertFalse(r["submission_ready"])
        self.assertTrue(r["passed"])

    # --- AC-13 术语证据区间豁免 -------------------------------------------
    def test_AC13_obsolete_term_scope(self):
        r = VE.verify(payload(report=report_text() + "\n旧称"), tools=FakeTools())
        self.assertIs(r["checks"]["vrf-08"], False)
        wrapped = (report_text() + "\n<!-- EVIDENCE-FRAGMENT-START -->\n旧称"
                   "\n<!-- EVIDENCE-FRAGMENT-END -->")
        r2 = VE.verify(payload(report=wrapped), tools=FakeTools())
        self.assertIs(r2["checks"]["vrf-08"], True)

    # --- AC-15 输出契约 ----------------------------------------------------
    def test_AC15_machine_readable_schema(self):
        r = VE.verify(payload(), tools=FakeTools())
        self.assertEqual(r["schema_version"], VE.SCHEMA_VERSION)
        for key in ("schema_version", "checks", "blocking", "missing", "pending",
                    "failed_checks", "passed", "submission_ready"):
            with self.subTest(key=key):
                self.assertIn(key, r)
        self.assertEqual(set(r["checks"]), set(VE.CHECKS))
        self.assertEqual(len(r["checks"]), 9)

    # --- AC-16 退出码与摘要 -----------------------------------------------
    def test_AC16_exit_codes_and_summary(self):
        with tempfile.TemporaryDirectory() as d:
            pdf, arc = self._artifacts(d)
            good = os.path.join(d, "good.json")
            with open(good, "w", encoding="utf-8") as f:
                json.dump(payload(pdf=pdf, zip_path=arc), f)
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                self.assertEqual(VE.main(["--payload", good, "--summary"]), 0)
            self.assertIn("结论：通过", buf.getvalue())
            r = VE.verify(payload(report="# OSID: 12345"), tools=FakeTools())
            summary = VE.render_summary(r)
            self.assertIn("结论：阻断", summary)
            self.assertIn("阻断 ", summary)
            self.assertEqual(VE.render_summary(None), "")

    # --- AC-17 判据单一事实源 ---------------------------------------------
    def test_AC17_three_piece_judgement_reuses_registry(self):
        reg = VE._loot_registry()
        calls = []
        original = reg.fragment_pieces
        reg.fragment_pieces = lambda text: calls.append(text) or original(text)
        try:
            VE.verify(payload(frags=[frag(flag="OSAI{x}", raw=FRAGMENT_MD)],
                              panel={"standalone": "OSAI{x}"}), tools=FakeTools())
        finally:
            reg.fragment_pieces = original
        self.assertTrue(calls, "未复用登记簿 fragment_pieces（C1 单一事实源）")

    def test_AC17_scored_keys_have_single_source(self):
        """键集只定义一次：report_exam 与校验器引用同一常量（C1）。"""
        import tools.scored_targets as st
        from tools.report_exam import _types
        self.assertEqual(tuple(_types.SCORED_HOSTS), tuple(st.SCORED_HOSTS))
        self.assertEqual(tuple(VE.SCORED_TARGETS), tuple(st.SCORED_HOSTS))
        self.assertEqual(_types.STANDALONE_KEY, st.STANDALONE_KEY)

    # --- AC-16 续：脚本直跑入口（SKILL 文档写法）必须可用 -------------------
    def test_AC16_cli_runnable_as_script(self):
        """`python tools/verify_evidence.py` 直跑时 sys.path[0]=tools/，须自行补仓库根。"""
        import subprocess
        proc = subprocess.run([sys.executable, "tools/verify_evidence.py", "--help"],
                              cwd=ROOT, capture_output=True, text=True)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("--from-loot", proc.stdout)

    # --- AC-18 下游委托不破 -----------------------------------------------
    def test_AC18_downstream_delegation_intact(self):
        import importlib
        pkg = importlib.import_module("tools.report_exam.package")
        shared = pkg._shared()
        # 判据来自同一模块文件：schema 与检查项集合必须一致（同一对象不强求）
        self.assertEqual(shared.SCHEMA_VERSION, VE.SCHEMA_VERSION)
        self.assertEqual(tuple(shared.CHECKS), tuple(VE.CHECKS))
        self.assertEqual(shared.verify(payload(), require_artifacts=False)["checks"],
                         VE.verify(payload(), require_artifacts=False)["checks"])



if __name__ == "__main__":
    unittest.main()
