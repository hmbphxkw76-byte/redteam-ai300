import contextlib
import copy
import io
import json
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from tools.pyrit_compat import checker, compat, manifest, mapper, model
from tools.pyrit_compat.alert import count_errors
from tools.pyrit_compat.model import Alert

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "tools" / "pyrit_compat" / "data"


class CompatTests(unittest.TestCase):
    def test_resolve_import_rejects_legacy(self):
        self.assertEqual(
            compat.resolve_import("pyrit.setup", "initialize_pyrit_async", "1.2.1"),
            ("pyrit.setup", "initialize_pyrit_async"))
        with self.assertRaises(compat.CompatibilityError):
            compat.resolve_import("pyrit.common", "initialize_pyrit_async", "1.2.1")

    def test_adapt_kwargs(self):
        with self.assertRaises(compat.CompatibilityError):
            compat.adapt_kwargs("pyrit.prompt_target.HTTPTarget", {"http_target": "x"}, "1.2.1")
        with self.assertRaises(compat.CompatibilityError):
            compat.adapt_kwargs("pyrit.prompt_target.HTTPTarget", {"trace_config": object()}, "1.1.0")
        adapted, alerts = compat.adapt_kwargs(
            "pyrit.executor.attack.PromptSendingAttack",
            {"params_type": "AttackParameters"}, "1.2.1")
        self.assertEqual(adapted["params_type"], "PromptSendingAttackParameters")
        self.assertTrue(any(a.severity == "warn" for a in alerts))

    def test_runtime_version_guard(self):
        with mock.patch("tools.pyrit_compat.compat.metadata.version", return_value="1.2.0"):
            with self.assertRaises(compat.CompatibilityError):
                compat.require_runtime_version("1.2.1")
        with mock.patch("tools.pyrit_compat.compat.metadata.version", return_value="1.2.1"):
            alert = compat.require_runtime_version("1.2.1")
            self.assertEqual(alert.code, "PYRIT_VERSION_OK")

    def test_signature_alerts(self):
        bundle = manifest.load_bundle(DATA)
        alerts = compat.signature_alerts({"symbols": bundle.signatures}, "1.1.0", "1.2.1")
        codes = {a.code for a in alerts}
        self.assertIn("PARAM_ADDED", codes)
        self.assertIn("DEFAULT_CHANGED", codes)
        self.assertNotIn("PARAM_REMOVED", codes)
        self.assertEqual(count_errors(alerts), 0)

    def test_rule_registry_reset(self):
        compat.reset_rules()
        self.assertTrue(compat.get_rules())


class CheckerTests(unittest.TestCase):
    def test_selftest(self):
        self.assertEqual(checker.main(["selftest"]), 0)

    def test_lock_generator(self):
        with contextlib.redirect_stdout(io.StringIO()) as output:
            status = checker.main(["lock", "--version", "1.2.1"])
        self.assertEqual(status, 0)
        self.assertIn("--hash=sha256:4e404c41", output.getvalue())
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(checker.main(["lock", "--version", "9.9.9"]), 3)

    def test_detect_from_version_facts(self):
        with contextlib.redirect_stdout(io.StringIO()) as output:
            status = checker.main(["detect", "--data-dir", str(DATA)])
        self.assertEqual(status, 0)
        self.assertEqual(json.loads(output.getvalue())["version"], "1.2.1")

    def test_map_output(self):
        with tempfile.TemporaryDirectory() as directory:
            out = Path(directory) / "map.json"
            self.assertEqual(checker.main(["map", "--root", str(ROOT), "--out", str(out)]), 0)
            report = json.loads(out.read_text(encoding="utf-8"))
        self.assertEqual(report["coverage"]["unclassified_sites"], 0)

    def test_strict_check_passes(self):
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(checker.main(["check", "--root", str(ROOT), "--target", "1.2.1"]), 0)

    def test_fault_injection_blocks(self):
        fake = model.CallSite("tools/x.py", 1, "pyrit.score",
                              "pyrit.score.GandalfScorer", "<module>", "ImportFrom")
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(checker.main(["check", "--root", str(ROOT), "--target", "1.3.0"]), 2)
            with mock.patch.object(mapper, "scan", return_value=[fake]):
                self.assertEqual(checker.main(["check", "--root", str(ROOT)]), 2)
            deviation = [model.Alert("error", "BEHAVIOR_DEVIATION", "injected")]
            with mock.patch.object(checker.compat, "signature_alerts", return_value=deviation):
                self.assertEqual(checker.main(["check", "--root", str(ROOT)]), 2)


class ExtensibilityTests(unittest.TestCase):
    def test_new_version_requires_only_a_fact_file(self):
        with tempfile.TemporaryDirectory() as directory:
            data_dir = Path(directory) / "data"
            versions = data_dir / "versions"
            versions.mkdir(parents=True)
            for source in (DATA / "versions").glob("*.json"):
                shutil.copy(source, versions / source.name)

            payload = copy.deepcopy(json.loads(
                (versions / "1.2.1.json").read_text(encoding="utf-8")))
            payload["version"] = "1.3.0"
            payload["release"]["version"] = "1.3.0"
            payload["release"]["release_notes_url"] = "https://example.invalid/v1.3.0"
            # 版本文件内每个符号直接存该版本的快照；新版本复用 1.2.1 快照即可。
            payload["signatures"] = copy.deepcopy(payload["signatures"])
            payload["changes"] = [{
                "id": "CHG-130", "category": "api", "status": "added",
                "symbol": "pyrit.future.NewApi", "version_from": "1.3.0",
                "version_to": "1.4.0", "detail": "synthetic future API",
                "source_url": "https://example.invalid/chg-130",
                "verified_at": "2026-11-24", "verification": "verified",
                "adaptation": "none", "adaptation_note": "test fixture",
            }]
            payload["adapters"] = [{
                "id": "ADP-130", "symbol": "pyrit.future.NewApi", "since": "1.3.0",
                "actions": [{"kind": "require_param", "param": "objective"}],
            }]
            (versions / "1.3.0.json").write_text(
                json.dumps(payload, ensure_ascii=False), encoding="utf-8")

            with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                status = checker.main(["check", "--root", str(ROOT),
                                       "--target", "1.3.0", "--data-dir", str(data_dir)])
            self.assertEqual(status, 0)
            bundle = manifest.load_bundle(data_dir)
            self.assertIn("1.3.0", bundle.versions)
            self.assertIn("CHG-130", {c.id for c in bundle.for_version("1.3.0")})
            rules = bundle.adapters_for("1.3.0")
            self.assertTrue(any(r["id"] == "ADP-130" for r in rules))


if __name__ == "__main__":
    unittest.main()
