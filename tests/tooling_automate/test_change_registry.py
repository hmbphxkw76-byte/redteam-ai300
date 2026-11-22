"""变更登记/清理契约测试（Ch11 模板 2 · AC-1/2/5）。

只断言外部行为：`--note` 结构化注记 → manifest 行字段 → 默认空串兼容；
`--strict` 对「登记变更但清理 pending」不阻断（诚实标注，不假称已清理）。
"""
import json
import os
import subprocess
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CLI = os.path.join(ROOT, "tools", "collect_evidence.py")


def run(*args):
    return subprocess.run([sys.executable, CLI, *args], capture_output=True, text=True, cwd=ROOT)


class ChangeRegistryTests(unittest.TestCase):
    def _manifest_record(self, tmp, note=None, strict=False):
        out = os.path.join(tmp, "out.md")
        man = os.path.join(tmp, "manifest.jsonl")
        shot = os.path.join(tmp, "s.png")
        with open(shot, "wb") as f:
            f.write(b"\x89PNG\r\n\x1a\n")
        argv = ["--step", "sc-05b", "--cmd", "echo change", "--output", "registered",
                "--screenshot", shot, "--manifest", man, "--out", out]
        if note is not None:
            argv += ["--note", note]
        if strict:
            argv += ["--strict"]
        r = run(*argv)
        with open(man, encoding="utf-8") as f:
            rec = json.loads(f.read().splitlines()[0])
        return r, rec

    def test_ac1_new_fields_default_empty_backward_compatible(self):
        with tempfile.TemporaryDirectory() as tmp:
            r, rec = self._manifest_record(tmp)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            for key in ("change_kind", "change_target", "change_ts", "cleanup_state", "cleanup_owner"):
                self.assertEqual(rec[key], "", "%s 应默认空串" % key)

    def test_ac2_structured_note_populates_change_fields(self):
        note = json.dumps({"change_kind": "module-hijack", "change_target": "sales_calc.py",
                           "change_ts": "2026-11-22T10:00:00", "cleanup_state": "done",
                           "cleanup_owner": "operator"}, ensure_ascii=False)
        with tempfile.TemporaryDirectory() as tmp:
            r, rec = self._manifest_record(tmp, note=note)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            self.assertEqual(rec["change_kind"], "module-hijack")
            self.assertEqual(rec["change_target"], "sales_calc.py")
            self.assertEqual(rec["cleanup_state"], "done")
            self.assertEqual(rec["cleanup_owner"], "operator")

    def test_ac5_pending_recorded_honestly_strict_not_blocked(self):
        # 登记了变更但未声明清理 → cleanup_state=pending；--strict 不阻断（如实标注）。
        note = json.dumps({"change_kind": "disable-defender"}, ensure_ascii=False)
        with tempfile.TemporaryDirectory() as tmp:
            r, rec = self._manifest_record(tmp, note=note, strict=True)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            self.assertEqual(rec["cleanup_state"], "pending")

    def test_plain_note_remains_analysis_note(self):
        with tempfile.TemporaryDirectory() as tmp:
            r, rec = self._manifest_record(tmp, note="这是一段普通分析注记")
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            self.assertEqual(rec["change_kind"], "")


if __name__ == "__main__":
    unittest.main()
