import json
import unittest
from pathlib import Path

from tools.pyrit_compat import manifest, mapper
from tools.pyrit_compat.version import TARGET_VERSION

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "tools" / "pyrit_compat" / "data"


class ManifestTests(unittest.TestCase):
    def test_load_and_validate(self):
        bundle = manifest.load_bundle(DATA)
        self.assertEqual(bundle.versions, ["1.1.0", "1.2.0", "1.2.1"])
        self.assertGreaterEqual(len(bundle.changes), 15)
        self.assertTrue(all(r.verification == "verified" for r in bundle.changes))
        self.assertTrue(all(r.source_url.startswith("https://") for r in bundle.changes))

    def test_version_filter(self):
        bundle = manifest.load_bundle(DATA)
        ids = {r.id for r in bundle.for_version(TARGET_VERSION)}
        self.assertIn("CHG-001", ids)
        self.assertIn("CHG-011", ids)
        self.assertNotIn("CHG-011", {r.id for r in bundle.for_version("1.2.0")})
        self.assertEqual(bundle.unverified(TARGET_VERSION), [])


class MapperTests(unittest.TestCase):
    def test_scan_classify_and_coverage(self):
        bundle = manifest.load_bundle(DATA)
        sites = mapper.scan(ROOT)
        self.assertTrue(any("pyrit" in s.symbol for s in sites))
        rows = mapper.classify(sites, bundle.changes, {"symbols": bundle.signatures})
        cov = mapper.coverage(rows)
        self.assertEqual(cov["unclassified_sites"], 0, json.dumps(rows, ensure_ascii=False))
        self.assertEqual(cov["coverage"], 1.0)

    def test_no_legacy_or_hook_drift(self):
        self.assertEqual(mapper.legacy_alerts(ROOT), [])
        self.assertEqual(mapper.hook_alerts(ROOT), [])


if __name__ == "__main__":
    unittest.main()
