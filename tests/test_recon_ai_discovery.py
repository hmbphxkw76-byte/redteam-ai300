#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""AC-01/AC-02：应用族发现与未决面闭环（不把未知伪装成资产）。"""
import os
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "tests"))

import recon_ai_fixtures as fx  # noqa: E402
from tools.recon_ai import discovery  # noqa: E402
from tools.recon_ai.model import Existence  # noqa: E402
from tools.recon_ai.transport import FakeTransport  # noqa: E402


class DiscoveryTests(unittest.TestCase):
    def test_streamlit_family_base_and_version(self):
        plan = discovery.discover(fx.TARGET_STREAMLIT,
                                  FakeTransport(fx.streamlit_routes()))
        self.assertEqual(plan.family, "streamlit")
        self.assertEqual(plan.base_path, "/chat")
        self.assertEqual(plan.version, "1.67.0")
        self.assertTrue(plan.basis)
        self.assertLessEqual(len(plan.results), discovery.MAX_DISCOVERY_REQUESTS)

    def test_entry_with_file_path_discovers_origin_app_family(self):
        plan = discovery.discover(
            fx.TARGET_STREAMLIT + "/reports/2026-11-15_ai_weekly.html",
            FakeTransport(fx.streamlit_routes()))
        self.assertEqual(plan.family, "streamlit")
        self.assertEqual(plan.base_path, "/chat")
        self.assertIn("origin", "".join(plan.basis))

    def test_candidate_bases_skip_files_and_deep_paths(self):
        bases = discovery._candidate_bases(
            '<a href="/chat">a</a><a href="/reports/x.html">b</a>'
            '<a href="/a/b/c/d">c</a><a href="https://x/y">d</a>')
        self.assertEqual(bases, ["/chat"])

    def test_unreachable_root_degrades_without_exception(self):
        plan = discovery.discover("http://127.0.0.1:1", FakeTransport({}))
        self.assertEqual(plan.family, "unknown")
        self.assertTrue(plan.basis)


class StreamlitClosedLoopTests(unittest.TestCase):
    def test_streamlit_chat_frontend_present_others_undetermined(self):
        with tempfile.TemporaryDirectory() as tmp:
            report = fx.run_fake(tmp, fx.streamlit_routes(),
                                 target=fx.TARGET_STREAMLIT)
            with open(report.report_md, encoding="utf-8") as f:
                text = f.read()
            with open(report.run_json, encoding="utf-8") as f:
                meta = __import__("json").load(f)
        self.assertEqual(len(report.judgements), 7)
        chat = report.judgements["recon-02"]
        self.assertEqual(chat.existence, Existence.PRESENT)
        self.assertIn("Streamlit", chat.product)
        others = [j for sid, j in report.judgements.items() if sid != "recon-02"]
        self.assertTrue(all(j.existence == Existence.UNDETERMINED
                            for j in others))
        self.assertEqual(len(report.inventory.assets), 1)
        self.assertEqual(report.inventory.assets[0].category, "模型服务")
        self.assertEqual(report.inventory.assets[0].endpoint,
                         fx.TARGET_STREAMLIT + "/chat/")
        self.assertEqual(len(report.inventory.gaps), 6)
        self.assertFalse(report.inventory.decoy_suspected)
        for step in meta["steps"]:
            self.assertEqual(step["status"], "done")
            self.assertTrue(step["basis"])
            self.assertTrue(step["tried"])
        self.assertIn("## 3. 缺口台账", text)
        self.assertIn("应用族", text)
        self.assertIn("- **判定**：PASS", text)
        self.assertEqual(report.verification.verdict, "PASS")

    def test_rag_terms_in_discovery_bundle_are_still_judged(self):
        routes = fx.streamlit_routes()
        routes[("GET", fx.TARGET_STREAMLIT + "/chat/static/js/index.DormvYxC.js")] = \
            fx.HttpResponse(200, "const version:`1.67.0`; var vectorstore=1;",
                            {}, "application/javascript")
        with tempfile.TemporaryDirectory() as tmp:
            report = fx.run_fake(tmp, routes, target=fx.TARGET_STREAMLIT)
        self.assertEqual(report.judgements["recon-03"].existence,
                         Existence.PRESENT)

    def test_frontend_embedding_id_does_not_fake_rag(self):
        routes = fx.streamlit_routes()
        routes[("GET", fx.TARGET_STREAMLIT + "/chat/static/js/index.DormvYxC.js")] = \
            fx.HttpResponse(200, "const version:`1.67.0`; var embeddingId=1;",
                            {}, "application/javascript")
        with tempfile.TemporaryDirectory() as tmp:
            report = fx.run_fake(tmp, routes, target=fx.TARGET_STREAMLIT)
        self.assertEqual(report.judgements["recon-03"].existence,
                         Existence.UNDETERMINED)
        self.assertEqual(report.verification.verdict, "PASS")


class DvaaClosedLoopTests(unittest.TestCase):
    def test_dvaa_family_inventory_recon_and_no_false_decoy(self):
        with tempfile.TemporaryDirectory() as tmp:
            report = fx.run_fake(tmp, fx.dvaa_routes(), target=fx.TARGET_DVAA)
            with open(report.report_md, encoding="utf-8") as f:
                text = f.read()
        self.assertEqual(report.judgements["recon-01"].existence,
                         Existence.PRESENT)
        self.assertIn("dvaa-llm", report.judgements["recon-01"].note)
        self.assertEqual(report.judgements["recon-02"].existence,
                         Existence.PRESENT)
        self.assertTrue(report.judgements["recon-02"].context.get("chat")
                        is not None)
        self.assertIn("helperbot",
                      report.judgements["recon-02"].context["chat"].url)
        self.assertEqual(report.judgements["recon-05"].existence,
                         Existence.PRESENT)
        self.assertIn("4 agents", report.judgements["recon-05"].product)
        self.assertEqual(report.judgements["recon-06"].existence,
                         Existence.PRESENT)
        self.assertTrue(report.judgements["recon-06"]
                        .context["endpoint"].endswith("/mcp/tools"))
        self.assertEqual(report.judgements["recon-07"].existence,
                         Existence.PRESENT)
        self.assertFalse(report.inventory.decoy_suspected)
        self.assertIn("多智能体", text)
        self.assertEqual(report.verification.verdict, "PASS")

    def test_dvaa_chooses_low_barrier_chat_agent(self):
        plan = discovery.discover(fx.TARGET_DVAA,
                                  FakeTransport(fx.dvaa_routes()))
        self.assertEqual(plan.family, "dvaa")
        self.assertEqual(plan.chat_agent_id, "helperbot")
        self.assertEqual(plan.agent_count, 4)
        self.assertEqual(plan.mcp_agent_count, 2)
        self.assertEqual(plan.llm_model, "dvaa-llm")


if __name__ == "__main__":
    unittest.main()
