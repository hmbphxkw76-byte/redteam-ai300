#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""通用目标适配回归：静态资源不得充当基路径、脚本产物按真实布局采集、
画像缺角色映射时不得把占位符发往目标。

对应本轮验证发现的三处非通用实现（见 docs/operations/skill-tool-verification 报告）：
  - `_candidate_bases` 依赖扩展名白名单 → favicon.ico / site.webmanifest 被当基路径；
  - `BUNDLE_RE` 硬限定 `/assets/` 前缀与双引号 → 非 Vite 布局（/js/app.js）漏采；
  - 画像缺 lab 映射时 `<LAB_ID>` 字面量被拼进 URL 外发。
"""
import os
import sys
import tempfile
import unittest

from tests._paths import ROOT  # noqa: E402
sys.path.insert(0, ROOT)

from tools import target_profile  # noqa: E402
from tools.recon_ai import discovery, probes, runner  # noqa: E402
from tools.recon_ai.transport import FakeTransport, HttpResponse  # noqa: E402

SPA = "<!doctype html><html><body><div id='root'></div></body></html>"


class StaticAssetIsNotBasePathTests(unittest.TestCase):
    """静态文件末段含「.」，任何站点都不应被当作应用基路径。"""

    def test_dotted_last_segment_rejected(self):
        bases = discovery._candidate_bases(
            '<link href="/favicon.ico"><link href="/site.webmanifest">'
            '<a href="/chat">ok</a>')
        self.assertEqual(bases, ["/chat"])

    def test_extensionless_paths_still_accepted(self):
        bases = discovery._candidate_bases(
            '<a href="/portal">a</a><a href="/lab/ui">b</a>')
        self.assertEqual(bases, ["/portal", "/lab/ui"])


class BundleDiscoveryTests(unittest.TestCase):
    """脚本产物采集须覆盖任意 .js 布局与引号风格。"""

    def test_script_single_quote_non_assets_layout(self):
        resp = HttpResponse(200, '<script type="module" src="/js/app.js"></script>',
                            {}, "text/html")
        resp.url = "http://host:9000/"
        self.assertEqual(probes._collect_bundle(resp)["bundle"],
                         "http://host:9000/js/app.js")

    def test_relative_script_resolved_against_entry_url(self):
        resp = HttpResponse(200, "<script src='js/app.js'></script>", {}, "text/html")
        resp.url = "http://host:9000/ui/"
        self.assertEqual(probes._collect_bundle(resp)["bundle"],
                         "http://host:9000/ui/js/app.js")

    def test_vite_hashed_bundle_still_supported(self):
        resp = HttpResponse(200, '<script src="/assets/index-BtcwQhVS.js"></script>',
                            {}, "text/html")
        resp.url = "http://host/"
        self.assertEqual(probes._collect_bundle(resp)["bundle"],
                         "http://host/assets/index-BtcwQhVS.js")


class UnresolvedPlaceholderTests(unittest.TestCase):
    """画像缺该角色映射时记「已跳过」，绝不放行 <LAB_ID> 到目标。"""

    def test_no_placeholder_leaves_the_process(self):
        profile = target_profile.from_mapping(
            {"name": "no-vector", "host": "dv.test:9000",
             "labs": {"chat": "c1"}})
        transport = FakeTransport(default=HttpResponse(200, SPA, {}, "text/html"))
        with tempfile.TemporaryDirectory() as tmp:
            report = runner.run_recon(
                target="http://dv.test:9000", out_dir=tmp, transport=transport,
                capture_shots=False, target_profile=profile)
            with open(report.report_md, encoding="utf-8") as handle:
                text = handle.read()
        urls = [call[1] for call in transport.calls]
        self.assertTrue(urls)
        self.assertFalse([u for u in urls if "<LAB_ID>" in u or "<TARGET>" in u])
        self.assertIn("已跳过", text)

    def test_mapped_role_is_still_probed(self):
        profile = target_profile.from_mapping(
            {"name": "with-vector", "host": "dv.test:9000",
             "labs": {"chat": "c1", "vector": "VEC_01"}})
        transport = FakeTransport(default=HttpResponse(200, SPA, {}, "text/html"))
        with tempfile.TemporaryDirectory() as tmp:
            runner.run_recon(
                target="http://dv.test:9000", out_dir=tmp, transport=transport,
                capture_shots=False, target_profile=profile)
        urls = [call[1] for call in transport.calls]
        self.assertIn("http://dv.test:9000/api/labs/VEC_01/summary", urls)


if __name__ == "__main__":
    unittest.main()
