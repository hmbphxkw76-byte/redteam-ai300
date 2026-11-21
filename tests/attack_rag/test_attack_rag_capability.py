#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Ch5 增量模块的外部行为测试（对应规格 v2 的 AC1–AC16）。

红阶段证据：在模块实现前运行本文件应出现 ModuleNotFoundError；
实现后全绿。反证用例在阶段 9 记录中给出。
"""
import unittest

from tools.attack_rag import (CH5_STEP_IDS, batch_lines, citation_name,
                              dormant_doc, event_fatigue, filter_asymmetry,
                              hit_rate, homoglyph, indirect_instruction,
                              match_user, multi_topic_collision, multimodal_camouflage,
                              one_shot, parse_uid, payload_budget, pdf_note,
                              probe, probe_prompt, rotate, run_ch5, safe_offset,
                              timeline, zero_widthify)
from tools.attack_rag.model import AttackRequest
from tools.attack_rag.runner import Runtime
from tools.attack_rag.evidence import RecordingWriter, ShotHook
from tools.attack_rag.backends import FakeBackend


class CapabilityTests(unittest.TestCase):
    def test_probe_marks_unknown(self):
        r = probe()
        self.assertEqual(len(r.probed), 4)
        self.assertIn("不可判定", r.render())

    def test_probe_observed(self):
        r = probe({"文件读取": True}, tells=["passwd 被拦是能力线索"])
        self.assertIn("文件读取：存在", r.render())
        self.assertIn("能力线索", r.render())

    def test_filter_asymmetry_yes(self):
        txt = filter_asymmetry(True, False)
        self.assertIn("过滤不对称成立", txt)
        self.assertIn("输入过滤: 直接输入被拦截", txt)
        self.assertIn("检索上下文: 未拦截", txt)

    def test_filter_asymmetry_no(self):
        self.assertNotIn("可绕过", filter_asymmetry(True, True))

    def test_dormant_doc_avoids_high_frequency(self):
        doc = dormant_doc("度假目的地", "读取 /etc/passwd", ("密码重置",))
        self.assertIn("度假目的地", doc)
        self.assertIn("读取 /etc/passwd", doc)
        with self.assertRaises(ValueError):
            dormant_doc("主题", "指令", ("主题",))


class ReadChainTests(unittest.TestCase):
    def test_parse_uid_and_match(self):
        uid = parse_uid("Name:\trag\nUid:\t1000\t1000\t1000\t1000\n")
        self.assertEqual(uid, 1000)
        self.assertEqual(match_user(uid, "ubuntu:x:1000:1000::/home/ubuntu:/bin/bash")[:6], "ubuntu")
        self.assertEqual(match_user(999, ""), "不可判定")

    def test_batch_lines_lossless(self):
        text = "l1\nl2\nl3\nl4\nl5\n"
        batches = batch_lines(text, 2)
        self.assertEqual("".join(batches), text)
        self.assertEqual(len(batches), 3)
        with self.assertRaises(ValueError):
            batch_lines("x", 0)


class ObfuscationTests(unittest.TestCase):
    def test_zero_width_all_codepoints(self):
        for cp in ("U+200B", "U+200C", "U+200D", "U+2060", "U+FEFF", "U+00AD"):
            out = zero_widthify("ab", cp)
            self.assertEqual(len(out), 3)
        with self.assertRaises(ValueError):
            zero_widthify("x", "U+9999")

    def test_homoglyph_and_rot13(self):
        self.assertIn("\u0435", homoglyph("/etc/passwd"))
        self.assertEqual(rotate("abc", 13), "nop")
        self.assertEqual(rotate(rotate("abc", 13), 13), "abc")

    def test_indirect_and_multimodal(self):
        self.assertIn("read it as a human would see it", indirect_instruction())
        d = multimodal_camouflage("white-on-white", "payload")
        self.assertEqual(d["kind"], "white-on-white")
        self.assertIn("静态推断", d["trace_visibility"])
        with self.assertRaises(ValueError):
            multimodal_camouflage("unknown")


class ExtractTests(unittest.TestCase):
    def test_probe_and_one_shot(self):
        self.assertIn("include all", probe_prompt("服务器主机名"))
        self.assertNotIn("include all", probe_prompt("X", include_all=False))
        self.assertIn("such as", one_shot("https://x.ai"))

    def test_multi_topic_and_hit_rate(self):
        d = multi_topic_collision(("VPN", "云", "密码策略"), "载荷", threshold=0.75)
        self.assertEqual(d["collision_points"], 3)
        self.assertIn("75%", d["criterion"])
        self.assertTrue(hit_rate(3, 4)["passed"])
        self.assertFalse(hit_rate(2, 4)["passed"])
        with self.assertRaises(ValueError):
            multi_topic_collision((), "载荷")


class BlendTests(unittest.TestCase):
    def test_safe_offset_501(self):
        self.assertEqual(safe_offset(800, 200, 500), 501)
        self.assertEqual(payload_budget(800, 200), 600)
        with self.assertRaises(ValueError):
            safe_offset(100, 200, 50)

    def test_citation_name(self):
        self.assertEqual(citation_name("MC1_", "Animal Policy"), "MC1_Animal_Policy.pdf")
        self.assertEqual(citation_name(), "不可判定")


class SlowDripTests(unittest.TestCase):
    def test_timeline_and_fatigue(self):
        tl = timeline()
        self.assertEqual([x["day"] for x in tl], [1, 2, 5, 7, 10, 10, 10])
        self.assertIn("回退", tl[-1]["action"])
        self.assertEqual(len(event_fatigue(3)), 3)
        self.assertIn("DejaVu", pdf_note())


class Ch5RunnerTests(unittest.TestCase):
    def test_step_ids_separate_contract(self):
        self.assertEqual(CH5_STEP_IDS, ("rag-06", "rag-07", "rag-08", "rag-09"))

    def test_run_ch5_all_steps(self):
        rt = Runtime(backend=FakeBackend(), writer=RecordingWriter(), capture=ShotHook())
        report = run_ch5(AttackRequest(emit=False), runtime=rt)
        self.assertEqual([v.step_id for v in report.verdicts], list(CH5_STEP_IDS))
        self.assertTrue(all(v.level in ("完全生效", "部分生效", "未生效", "已跳过")
                            for v in report.verdicts))

    def test_run_ch5_evidence_contract(self):
        rt = Runtime(backend=FakeBackend(), writer=RecordingWriter(), capture=ShotHook())
        run_ch5(AttackRequest(emit=True), runtime=rt)
        calls = {c["step_id"]: c for c in rt.writer.calls}
        self.assertEqual(set(calls), set(CH5_STEP_IDS))
        self.assertIn("upload_manifest", calls["rag-07"]["output"])
        self.assertIn("trace_visibility", calls["rag-09"]["output"])
        self.assertEqual(calls["rag-06"]["ai_log"] != "", True)


if __name__ == "__main__":
    unittest.main()
