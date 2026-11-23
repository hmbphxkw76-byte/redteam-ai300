import json
import tempfile
import unittest
from pathlib import Path

from tools.pyrit_compat.version import Version, in_range
from tools.pyrit_compat.versions import FixtureReleaseSource, latest


class VersionTests(unittest.TestCase):
    def test_parse_and_compare(self):
        self.assertEqual(str(Version("v1.2.1")), "1.2.1")
        self.assertLess(Version("1.2.0"), Version("1.2.1"))
        self.assertEqual(Version("1.2"), Version("1.2.0"))
        with self.assertRaises(ValueError):
            Version("1.x.0")

    def test_range(self):
        self.assertTrue(in_range("1.2.0", "1.2.0", "1.3.0"))
        self.assertFalse(in_range("1.3.0", "1.2.0", "1.3.0"))
        self.assertFalse(in_range("1.1.0", "1.2.0", None))

    def test_fixture_detection(self):
        payload = {"releases": {
            "1.1.0": [{"upload_time_iso_8601": "2026-09-04T00:00:00Z", "url": "u", "digests": {"sha256": "a"}}],
            "1.2.0": [{"upload_time_iso_8601": "2026-11-13T00:00:00Z", "url": "u", "digests": {"sha256": "b"}}],
            "1.2.1": [{"upload_time_iso_8601": "2026-11-16T00:00:00Z", "url": "u", "digests": {"sha256": "c"}}],
            "1.3.0rc0": [{"upload_time_iso_8601": "2026-11-20T00:00:00Z", "url": "u", "digests": {"sha256": "d"}}],
        }}
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "releases.json"
            path.write_text(json.dumps(payload), encoding="utf-8")
            release = latest(FixtureReleaseSource(path), "1.2.0")
        self.assertEqual(release.version, "1.2.1")
        self.assertEqual(release.sha256, "c")


if __name__ == "__main__":
    unittest.main()
