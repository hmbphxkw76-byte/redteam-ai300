#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Ch2 影子端点（C8）：声明/引用差集、归一化、置信度与集成。"""
import unittest

from tools.recon_ai import ch2, shadow


class NormalizeTest(unittest.TestCase):
    def test_strips_query_fragment_and_trailing_slash(self):
        self.assertEqual(shadow.normalize_path("/api/orders/?x=1#top"), "/api/orders")
        self.assertEqual(shadow.normalize_path("/api/v1/users/"), "/api/v1/users")

    def test_numeric_and_guid_segments_become_id(self):
        self.assertEqual(shadow.normalize_path("/api/orders/42"), "/api/orders/{id}")
        guid = "123e4567-e89b-12d3-a456-426614174000"
        self.assertEqual(shadow.normalize_path("/api/items/%s" % guid), "/api/items/{id}")

    def test_collapses_duplicate_slashes_and_rejects_relative(self):
        self.assertEqual(shadow.normalize_path("//api//orders"), "/api/orders")
        self.assertEqual(shadow.normalize_path("api/orders"), "")
        self.assertEqual(shadow.normalize_path("/"), "")


class DeclaredTest(unittest.TestCase):
    def test_openapi_mapping_and_bare_list(self):
        declared = shadow.declared_paths({"paths": {"/api/chat": {}, "/api/orders/{id}": {}}})
        self.assertEqual(declared, ("/api/chat", "/api/orders/{id}"))
        self.assertEqual(shadow.declared_paths(["/api/chat"]), ("/api/chat",))
        self.assertEqual(shadow.declared_paths(None), ())


class ObservedTest(unittest.TestCase):
    def test_extracts_literals_and_filters_noise(self):
        documents = [
            {"name": "app.js", "text": 'fetch("/api/chat"); axios.get("/internal/export");'},
            {"name": "index.html", "text": '<script src="/static/app.js"></script>'
                                           ' href="https://cdn.example.com/x/y"'},
        ]
        observed = shadow.observed_paths(documents)
        self.assertIn("/api/chat", observed)
        self.assertIn("/internal/export", observed)
        self.assertFalse(any(item.endswith(".js") for item in observed))
        self.assertFalse(any(item.startswith("//") for item in observed))


class CandidateTest(unittest.TestCase):
    def test_declared_and_templated_paths_excluded(self):
        candidates = shadow.shadow_candidates(
            declared=("/api/chat", "/api/orders/{id}"),
            observed=("/api/chat", "/api/orders/{id}", "/internal/export"),
        )
        self.assertEqual([c.path for c in candidates], ["/internal/export"])

    def test_confidence_high_vs_medium_and_counts(self):
        candidates = shadow.shadow_candidates(
            declared=(),
            observed=("/internal/export", "/internal/export", "/api/{id}"),
        )
        by_path = {c.path: c for c in candidates}
        self.assertEqual(by_path["/internal/export"].confidence, shadow.HIGH)
        self.assertEqual(by_path["/internal/export"].references, 2)
        self.assertEqual(by_path["/api/{id}"].confidence, shadow.MEDIUM)

    def test_deterministic_sorted_output(self):
        first = shadow.shadow_candidates((), ("/b/c", "/a/b"))
        second = shadow.shadow_candidates((), ("/a/b", "/b/c"))
        self.assertEqual([c.path for c in first], ["/a/b", "/b/c"])
        self.assertEqual([c.to_dict() for c in first], [c.to_dict() for c in second])


class AnalyzeTest(unittest.TestCase):
    def test_no_documents_is_undetermined(self):
        self.assertEqual(shadow.analyze({"openapi": {"paths": {}}}), {
            "status": "UNDETERMINED", "declared": [], "observed": [],
            "candidates": [], "basis": shadow.analyze({})["basis"],
        })

    def test_all_declared_is_absent(self):
        result = shadow.analyze({
            "openapi": {"paths": {"/api/chat": {}}},
            "documents": [{"name": "app.js", "text": 'fetch("/api/chat")'}],
        })
        self.assertEqual(result["status"], "ABSENT")
        self.assertEqual(result["candidates"], [])

    def test_candidates_present_with_basis(self):
        result = shadow.analyze({
            "openapi": {"paths": {"/api/chat": {}}},
            "documents": [{"name": "app.js", "text": 'fetch("/internal/report/export")'}],
        })
        self.assertEqual(result["status"], "PRESENT")
        self.assertEqual(result["candidates"][0]["path"], "/internal/report/export")
        self.assertIn("不等于端点可用", result["basis"])


class Ch2IntegrationTest(unittest.TestCase):
    def test_shadow_finding_joins_analysis_and_passes_validation(self):
        report = ch2.analyze({
            "target": "192.168.50.12",
            "observations": [{
                "kind": "shadow",
                "openapi": {"paths": {"/api/chat": {}}},
                "documents": [{"name": "gateway.js",
                               "text": 'fetch("/api/chat"); fetch("/internal/report/export");'
                                       ' fetch("/admin/debug/trace");'}],
            }],
        })
        finding = [f for f in report["findings"] if f["name"] == "影子端点"][0]
        self.assertEqual(finding["verdict"], "PRESENT")
        self.assertEqual(len(finding["signals"]), 2)
        self.assertTrue(all(s["kind"].startswith("shadow:") for s in finding["signals"]))
        self.assertEqual(ch2.validate_analysis(report), [])

    def test_declared_only_is_absent_and_valid(self):
        report = ch2.analyze({"observations": [{
            "kind": "shadow",
            "openapi": {"paths": {"/api/chat": {}}},
            "documents": [{"name": "app.js", "text": 'fetch("/api/chat")'}],
        }]})
        finding = [f for f in report["findings"] if f["name"] == "影子端点"][0]
        self.assertEqual(finding["verdict"], "ABSENT")
        self.assertEqual(ch2.validate_analysis(report), [])


if __name__ == "__main__":
    unittest.main()
