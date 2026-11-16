#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""attack-embeddings SKILL.md 点名脚本的行为测试（S2）。

覆盖 SKILL.md 显式列出的 4 个 CLI 入口（emb-03/04/05/06）：
  - 夹具模式的确定性输出与退出码；
  - 入参错误的非零退出码；
  - 目标不可达时的显式失败（不静默降级）；
  - 脚本文件与 SKILL.md 引用的一致性（防文档与实现漂移）。

仅依赖标准库。运行：python -m unittest discover -s tests
"""
import contextlib
import importlib.util
import io
import json
import os
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKILL = os.path.join(ROOT, "skills", "attack-embeddings", "SKILL.md")

# SKILL.md 点名的脚本 → 其负责的 step
NAMED_SCRIPTS = {
    "embed_invert.py": "emb-03",
    "membership_inference.py": "emb-04",
    "adv_embed.py": "emb-05",
    "vector_lookup.py": "emb-06",
}


def load_script(filename):
    """按路径加载 tools/<filename>，返回模块。"""
    path = os.path.join(ROOT, "tools", filename)
    spec = importlib.util.spec_from_file_location("ae_script_" + filename[:-3], path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def run_main(mod, argv):
    """调用脚本 main，捕获 stdout，返回 (exit_code, stdout)。"""
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        code = mod.main(argv)
    return code, buf.getvalue()


class SkillNamedScriptsPresenceTests(unittest.TestCase):
    def test_named_scripts_exist_and_are_referenced(self):
        with open(SKILL, encoding="utf-8") as f:
            text = f.read()
        for filename, step in NAMED_SCRIPTS.items():
            with self.subTest(script=filename):
                self.assertTrue(
                    os.path.isfile(os.path.join(ROOT, "tools", filename)),
                    "SKILL.md 点名的 tools/%s 不存在" % filename)
                self.assertIn("tools/" + filename, text,
                              "SKILL.md 未引用 tools/%s" % filename)
                self.assertIn(step, text)


class EmbedInvertScriptTests(unittest.TestCase):
    def setUp(self):
        self.mod = load_script("embed_invert.py")

    def test_fixture_exact_recovery(self):
        code, out = run_main(self.mod, ["--text", "salary executive package secret"])
        self.assertEqual(code, 0)
        self.assertIn("emb-03", out)
        payload = json.loads(out[out.index("{"):])
        self.assertEqual(payload["recovered_text"], "salary executive package secret")
        self.assertEqual(payload["confidence"], 1.0)
        self.assertEqual(payload["mode"], "fixture")

    def test_vec_roundtrip_via_file(self):
        with tempfile.TemporaryDirectory() as td:
            vec_path = os.path.join(td, "out.vec")
            code, _ = run_main(self.mod, ["--text", "password admin root token file",
                                         "--out-vec", vec_path])
            self.assertEqual(code, 0)
            self.assertTrue(os.path.isfile(vec_path))
            code, out = run_main(self.mod, ["--vec", vec_path])
            self.assertEqual(code, 0)
            payload = json.loads(out[out.index("{"):])
            self.assertEqual(payload["recovered_text"], "password admin root token file")

    def test_missing_input_returns_2(self):
        code, _ = run_main(self.mod, [])
        self.assertEqual(code, 2)

    def test_unreachable_endpoint_returns_3(self):
        code, _ = run_main(self.mod, ["--endpoint", "http://127.0.0.1:9", "--text", "x"])
        self.assertEqual(code, 3)


class MembershipScriptTests(unittest.TestCase):
    def setUp(self):
        self.mod = load_script("membership_inference.py")

    def test_member_detected(self):
        code, out = run_main(self.mod, ["--sample", "salary executive package secret"])
        self.assertEqual(code, 0)
        payload = json.loads(out[out.index("{"):])
        self.assertTrue(payload["verdict"] == "在集")
        self.assertAlmostEqual(payload["score"], 1.0, places=3)

    def test_nonmember_detected(self):
        code, out = run_main(self.mod, ["--sample", "unrelated external text"])
        self.assertEqual(code, 0)
        payload = json.loads(out[out.index("{"):])
        self.assertEqual(payload["verdict"], "非在集")

    def test_sample_from_file(self):
        with tempfile.TemporaryDirectory() as td:
            p = os.path.join(td, "suspect.txt")
            with open(p, "w", encoding="utf-8") as f:
                f.write("refund unlimited returns policy")
            code, out = run_main(self.mod, ["--sample", p])
            self.assertEqual(code, 0)
            self.assertIn("emb-04", out)

    def test_auc_with_labelled_sets(self):
        with tempfile.TemporaryDirectory() as td:
            mem = os.path.join(td, "m.json")
            non = os.path.join(td, "n.json")
            with open(mem, "w", encoding="utf-8") as f:
                json.dump(["salary executive package secret"], f)
            with open(non, "w", encoding="utf-8") as f:
                json.dump(["unrelated external text"], f)
            code, out = run_main(self.mod, ["--sample", "salary executive package secret",
                                            "--members", mem, "--nonmembers", non])
            self.assertEqual(code, 0)
            payload = json.loads(out[out.index("{"):])
            self.assertAlmostEqual(payload["auc"], 1.0, places=3)

    def test_empty_sample_returns_2(self):
        code, _ = run_main(self.mod, ["--sample", ""])
        self.assertEqual(code, 2)


class AdvEmbedScriptTests(unittest.TestCase):
    def setUp(self):
        self.mod = load_script("adv_embed.py")

    def test_shift_increases_similarity(self):
        code, out = run_main(self.mod, ["--text", "benign text alpha",
                                        "--target-text", "poison target query chunk"])
        self.assertEqual(code, 0)
        payload = json.loads(out[out.index("{"):])
        self.assertGreater(payload["delta"], 0.0)
        self.assertEqual(payload["verdict"], "扰动有效")
        self.assertTrue(payload["token_changed"])

    def test_high_eps_marks_insufficient(self):
        code, out = run_main(self.mod, ["--text", "benign text alpha", "--eps", "99"])
        self.assertEqual(code, 0)
        payload = json.loads(out[out.index("{"):])
        self.assertEqual(payload["verdict"], "扰动不足")

    def test_empty_text_returns_2(self):
        code, _ = run_main(self.mod, ["--text", "  "])
        self.assertEqual(code, 2)


class VectorLookupScriptTests(unittest.TestCase):
    def setUp(self):
        self.mod = load_script("vector_lookup.py")

    def test_lookup_hits_fixture_corpus(self):
        code, out = run_main(self.mod, ["--query", "salary executive", "--topk", "3"])
        self.assertEqual(code, 0)
        payload = json.loads(out[out.index("{"):])
        self.assertEqual(payload["hit_count"], 3)
        self.assertEqual(payload["hits"][0]["id"], "doc-1")
        self.assertEqual(payload["verdict"], "反查命中")

    def test_custom_corpus(self):
        with tempfile.TemporaryDirectory() as td:
            c = os.path.join(td, "corpus.json")
            with open(c, "w", encoding="utf-8") as f:
                json.dump({"d1": "credit card ssn", "d2": "alpha beta gamma"}, f)
            code, out = run_main(self.mod, ["--query", "credit card",
                                            "--corpus", c, "--topk", "2"])
            self.assertEqual(code, 0)
            payload = json.loads(out[out.index("{"):])
            self.assertEqual(payload["hit_count"], 2)
            self.assertEqual(payload["hits"][0]["id"], "d1")

    def test_bad_topk_returns_2(self):
        code, _ = run_main(self.mod, ["--query", "x", "--topk", "0"])
        self.assertEqual(code, 2)

    def test_empty_query_returns_2(self):
        code, _ = run_main(self.mod, ["--query", ""])
        self.assertEqual(code, 2)


if __name__ == "__main__":
    unittest.main()
