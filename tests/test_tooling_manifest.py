"""manifest 切片测试（AC-01/02/07/12）。"""
import json
import os
import tempfile
import unittest

from tools.tooling_automate import manifest as M

FIELDS = ("category", "target", "step", "inputs", "outputs", "trigger", "classification")


def write_manifest(tmp, tasks):
    p = os.path.join(tmp, "m.json")
    with open(p, "w", encoding="utf-8") as f:
        json.dump({"tasks": tasks}, f)
    return p


class TaskManifestTests(unittest.TestCase):
    def test_seven_fields_required(self):
        bad = {"category": "enum", "target": "h1", "step": "e-01",
               "inputs": {"cmd": "x"}, "outputs": {}, "trigger": "t"}
        # 缺 classification
        with tempfile.TemporaryDirectory() as d:
            p = write_manifest(d, [bad])
            with self.assertRaises(M.UsageError):
                M.load_manifest(p)

    def test_manual_classification(self):
        tasks = [
            {"category": "enum", "target": "h1", "step": "e-01",
             "inputs": {"cmd": "x"}, "outputs": {}, "trigger": "t", "classification": "auto"},
            {"category": "enum", "target": "h1", "step": "e-02",
             "inputs": {"cmd": "x"}, "outputs": {}, "trigger": "t", "classification": "manual"},
        ]
        with tempfile.TemporaryDirectory() as d:
            man = M.load_manifest(write_manifest(d, tasks))
        self.assertEqual(len(man.scriptable), 1)
        self.assertEqual(len(man.manual), 1)
        self.assertTrue(man.manual[0].is_manual)
        self.assertFalse(man.scriptable[0].is_manual)

    def test_step_namespace(self):
        self.assertEqual(M.parse_step("rag-07"), ("rag", 7))
        with self.assertRaises(M.UsageError):
            M.parse_step("bad-step")
        with self.assertRaises(M.UsageError):
            M.parse_step("rag-0")  # 非 NN 形式（无数字）

    def test_step_conflict(self):
        tasks = [
            {"category": "enum", "target": "h1", "step": "e-01",
             "inputs": {"cmd": "x"}, "outputs": {}, "trigger": "t", "classification": "auto"},
            {"category": "enum", "target": "h1", "step": "e-01",
             "inputs": {"cmd": "x"}, "outputs": {}, "trigger": "t", "classification": "auto"},
        ]
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(M.UsageError):
                M.load_manifest(write_manifest(d, tasks))

    def test_load_ok(self):
        tasks = [{"category": "enum", "target": "h1", "step": "e-01",
                  "inputs": {"cmd": "x"}, "outputs": {"evidence": "ev.md"},
                  "trigger": "t", "classification": "auto"}]
        with tempfile.TemporaryDirectory() as d:
            man = M.load_manifest(write_manifest(d, tasks))
        self.assertEqual(man.tasks[0].cmd, "x")


if __name__ == "__main__":
    unittest.main()
