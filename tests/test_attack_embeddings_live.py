#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""真实目标适配层（`live.py`）与脚本 live 路径测试（S2）。

用标准库 `http.server` 起本地桩服务，验证：
  - OpenAI 兼容 `/v1/models` 与 `/v1/embeddings` 的解析与异常；
  - HTTP 向量库检索的多种响应形状归一；
  - 4 个 CLI 脚本的 live 路径端到端（含不可达与畸形响应）。

仅依赖标准库。运行：python -m unittest discover -s tests
"""
import contextlib
import importlib.util
import io
import json
import os
import sys
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from unittest import mock

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from tools.attack_embeddings import live as live_mod  # noqa: E402
from tools.attack_embeddings.live import (  # noqa: E402
    LiveEmbeddingClient, LiveError, LiveVectorStoreClient, _normalize_matches)


class _StubHandler(BaseHTTPRequestHandler):
    """按路径返回预设响应，模拟真实端点/向量库。"""

    def _send(self, obj, status=200):
        body = json.dumps(obj).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):  # noqa: N802
        if self.path == "/v1/models":
            self._send({"data": [{"id": "m1"}, {"id": "m2"}, "m3"]})
        elif self.path == "/v1/models/nodata":
            self._send({"object": "list"})
        elif self.path == "/badjson":
            self._send_raw(b"not-json-at-all")
        else:
            self.send_error(404)

    def do_POST(self):  # noqa: N802
        length = int(self.headers.get("Content-Length") or 0)
        try:
            body = json.loads(self.rfile.read(length) or b"{}")
        except ValueError:
            body = {}
        if self.path == "/v1/embeddings":
            text = str(body.get("input", ""))
            vec = [float(len(t)) for t in text.split()] or [1.0]
            self._send({"data": [{"embedding": vec}]})
        elif self.path == "/store":
            self._send({"matches": [{"id": "d1", "score": 0.9, "text": "alpha"},
                                    {"id": "d2", "score": 0.1, "text": "beta"}]})
        elif self.path == "/store/results":
            self._send({"results": [{"doc_id": "x", "similarity": 0.5, "content": "y"}]})
        elif self.path == "/store/list":
            self._send([{"id": "z", "score": 0.3, "text": "w"}])
        elif self.path == "/store/empty":
            self._send({"object": "list"})
        else:
            self.send_error(404)

    def _send_raw(self, data, status=200):
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, *args):  # 静默，避免污染测试输出
        pass


class _StubServerCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), _StubHandler)
        cls.base = "http://127.0.0.1:%d" % cls.server.server_address[1]
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=5)


class LiveAdapterTests(_StubServerCase):
    def test_list_models(self):
        self.assertEqual(LiveEmbeddingClient(self.base).list_models(), ["m1", "m2", "m3"])

    def test_list_models_missing_data_raises(self):
        with self.assertRaises(LiveError):
            LiveEmbeddingClient(self.base + "/v1/models/nodata").list_models()

    def test_embed_returns_floats(self):
        vec = LiveEmbeddingClient(self.base).embed("alpha beta gamma")
        self.assertEqual(vec, [5.0, 4.0, 5.0])
        self.assertIsInstance(vec[0], float)

    def test_dimension(self):
        self.assertEqual(LiveEmbeddingClient(self.base).dimension("a bb"), 2)

    def test_embed_empty_text_raises(self):
        with self.assertRaises(LiveError):
            LiveEmbeddingClient(self.base).embed("   ")

    def test_embed_missing_field_raises(self):
        client = LiveEmbeddingClient(self.base)
        with mock.patch.object(live_mod, "_post_json",
                               return_value={"data": [{"no_embedding": True}]}):
            with self.assertRaises(LiveError):
                client.embed("x")

    def test_embed_nonlist_raises(self):
        client = LiveEmbeddingClient(self.base)
        with mock.patch.object(live_mod, "_post_json",
                               return_value={"data": [{"embedding": "oops"}]}):
            with self.assertRaises(LiveError):
                client.embed("x")

    def test_embed_empty_vector_raises(self):
        client = LiveEmbeddingClient(self.base)
        with mock.patch.object(live_mod, "_post_json",
                               return_value={"data": [{"embedding": []}]}):
            with self.assertRaises(LiveError):
                client.embed("x")

    def test_empty_base_url_raises(self):
        with self.assertRaises(LiveError):
            LiveEmbeddingClient("")

    def test_bad_json_raises(self):
        with self.assertRaises(LiveError):
            live_mod._get_json(self.base + "/badjson")

    def test_non_json_post_raises(self):
        with self.assertRaises(LiveError):
            live_mod._post_json(self.base + "/badjson", {})

    def test_store_query_vector(self):
        hits = LiveVectorStoreClient(self.base + "/store").query_vector([1.0, 2.0], 2)
        self.assertEqual(hits[0]["id"], "d1")
        self.assertAlmostEqual(hits[0]["sim"], 0.9)

    def test_store_query_text(self):
        self.assertEqual(len(LiveVectorStoreClient(self.base + "/store").query_text("a", 2)), 2)

    def test_store_results_shape(self):
        hits = LiveVectorStoreClient(self.base + "/store/results").query_vector([1.0], 1)
        self.assertEqual(hits[0]["id"], "x")
        self.assertAlmostEqual(hits[0]["sim"], 0.5)
        self.assertEqual(hits[0]["text"], "y")

    def test_store_list_shape(self):
        hits = LiveVectorStoreClient(self.base + "/store/list").query_vector([1.0], 1)
        self.assertEqual(hits[0]["id"], "z")

    def test_store_empty_returns_empty(self):
        self.assertEqual(
            LiveVectorStoreClient(self.base + "/store/empty").query_vector([1.0], 1), [])

    def test_store_empty_url_raises(self):
        with self.assertRaises(LiveError):
            LiveVectorStoreClient("")

    def test_store_unreachable_raises(self):
        with self.assertRaises(LiveError):
            LiveVectorStoreClient("http://127.0.0.1:9").query_text("a", 1)

    def test_normalize_ignores_non_dict(self):
        self.assertEqual(_normalize_matches({"matches": ["x", 1, None]}), [])
        self.assertEqual(_normalize_matches("nonsense"), [])


class ScriptLivePathTests(_StubServerCase):
    """4 个脚本的 live 路径端到端。"""

    def _load(self, filename):
        path = os.path.join(ROOT, "tools", filename)
        spec = importlib.util.spec_from_file_location("ae_live_" + filename[:-3], path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod

    def _run(self, mod, argv):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            code = mod.main(argv)
        return code, buf.getvalue()

    def _payload(self, out):
        return json.loads(out[out.index("{"):])

    def test_embed_invert_live(self):
        code, out = self._run(self._load("embed_invert.py"),
                              ["--endpoint", self.base, "--text", "alpha beta",
                               "--topk", "2"])
        self.assertEqual(code, 0)
        payload = self._payload(out)
        self.assertEqual(payload["mode"], "live")
        self.assertEqual(payload["dim"], 2)
        self.assertEqual(payload["candidate_pool"], "builtin-fixture")

    def test_embed_invert_live_with_corpus(self):
        with tempfile.TemporaryDirectory() as td:
            c = os.path.join(td, "corpus.json")
            with open(c, "w", encoding="utf-8") as f:
                json.dump({"d1": "alpha beta gamma"}, f)
            code, out = self._run(self._load("embed_invert.py"),
                                  ["--endpoint", self.base, "--text", "alpha",
                                   "--corpus", c, "--topk", "1"])
            self.assertEqual(code, 0)
            self.assertEqual(self._payload(out)["candidate_pool"], "corpus")

    def test_membership_live(self):
        code, out = self._run(self._load("membership_inference.py"),
                              ["--endpoint", self.base, "--sample", "alpha",
                               "--threshold", "0"])
        self.assertEqual(code, 0)
        payload = self._payload(out)
        self.assertEqual(payload["mode"], "live")
        self.assertEqual(payload["verdict"], "在集")

    def test_adv_embed_live(self):
        code, out = self._run(self._load("adv_embed.py"),
                              ["--endpoint", self.base, "--text", "alpha beta",
                               "--target-text", "alpha gamma", "--passes", "1"])
        self.assertEqual(code, 0)
        self.assertEqual(self._payload(out)["mode"], "live")

    def test_vector_lookup_live(self):
        code, out = self._run(self._load("vector_lookup.py"),
                              ["--store", self.base + "/store", "--query", "alpha",
                               "--topk", "2"])
        self.assertEqual(code, 0)
        payload = self._payload(out)
        self.assertEqual(payload["mode"], "live")
        self.assertEqual(payload["hit_count"], 2)

    def test_vector_lookup_live_corpus_with_embed_api(self):
        with tempfile.TemporaryDirectory() as td:
            c = os.path.join(td, "corpus.json")
            with open(c, "w", encoding="utf-8") as f:
                json.dump({"d1": "alpha"}, f)
            with mock.patch.dict(os.environ, {"EMBED_API": self.base}):
                code, out = self._run(self._load("vector_lookup.py"),
                                      ["--store", self.base + "/store", "--query", "alpha",
                                       "--corpus", c, "--topk", "2"])
            self.assertEqual(code, 0)
            self.assertEqual(self._payload(out)["hit_count"], 2)

    def test_vector_lookup_live_corpus_without_embed_api(self):
        with tempfile.TemporaryDirectory() as td:
            c = os.path.join(td, "corpus.json")
            with open(c, "w", encoding="utf-8") as f:
                json.dump({"d1": "alpha"}, f)
            env = {k: v for k, v in os.environ.items() if k != "EMBED_API"}
            with mock.patch.dict(os.environ, env, clear=True):
                code, _ = self._run(self._load("vector_lookup.py"),
                                    ["--store", self.base + "/store", "--query", "alpha",
                                     "--corpus", c])
            self.assertEqual(code, 2)


if __name__ == "__main__":
    unittest.main()
