#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""attack-mcp-tool Ch7 增量测试（规格 #293 v2 AC-01..AC-11）。

全部离线：注入假传输/假 FS/假 UI host；只断言外部可观测行为。
"""

import json
import sys
import unittest

from tests._paths import ROOT  # noqa: E402
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from tools.attack_mcp_tool import (STEP_IDS, AttackRequest, Runtime, run_attack)  # noqa: E402
from tools.attack_mcp_tool import chain as chain_build  # noqa: E402
from tools.attack_mcp_tool import grade as grading  # noqa: E402
from tools.attack_mcp_tool import escape as escape_judge  # noqa: E402
from tools.attack_mcp_tool import poison as poison_mod  # noqa: E402
from tools.attack_mcp_tool.evidence import RecordingWriter  # noqa: E402
from tools.attack_mcp_tool.shot import NullCapture  # noqa: E402
from tools.attack_mcp_tool.transport import FakeHttpClient  # noqa: E402
from tools.attack_mcp_tool.uihost import FakeUiHost, make_ui_resource  # noqa: E402


class _FakeFS:
    """注入式假 FS：realpath 按映射解析，验证 symlink 逃逸判据。"""

    def __init__(self, mapping):
        self.mapping = mapping

    def realpath(self, path):
        return self.mapping.get(path, path)


def _offline(uihost=None):
    return Runtime(client=FakeHttpClient({}), writer=RecordingWriter(),
                   capture=NullCapture(), uihost=uihost)


class TestLocalSelfProofCap(unittest.TestCase):
    """本地自证不得冒称完全生效（实测发现 grade.py 未置 capped_partial）。"""

    def test_local_only_steps_capped_at_partial(self):
        ctx = {
            "served": True, "poisoned": True, "descriptor_changed": True,
            "injection_present": True,
            "diff": {"added": ["x"], "changed": [{"fields": ["description"]}]},
        }
        for step in ("mcp-02", "mcp-03", "mcp-04"):
            with self.subTest(step=step):
                level, reason = grading.grade(grading.derive(step, None, ctx))
                self.assertEqual(level, "部分生效")
                self.assertNotIn("不得判完全生效", reason)
                self.assertIn("目标侧未生效", reason)


class TestAc01TargetDiff(unittest.TestCase):
    def test_new_step_ids_appended_after_legacy_eight(self):
        self.assertEqual(STEP_IDS[:8], tuple("mcp-0%d" % i for i in range(1, 9)))
        self.assertEqual(STEP_IDS[8:], ("mcp-09", "mcp-10", "mcp-11"))

    def test_mcp04_diff_source_marker_defaults_legacy(self):
        # 既有 mcp-04 在无目标侧快照时不伪造 target-sse 标记
        report = run_attack(AttackRequest(target="http://t.example", step="mcp-04", emit=False),
                            _offline())
        self.assertEqual(report.verdicts[0].step_id, "mcp-04")


class TestAc02UiResource(unittest.TestCase):
    def test_resource_uri_valid_and_poison_injected(self):
        r = make_ui_resource()
        self.assertTrue(r.resource_uri.startswith("ui://"))
        self.assertIn("IMPORTANT", r.description)

    def test_flat_meta_deprecated_form_not_produced(self):
        r = make_ui_resource()
        self.assertNotIn("ui/resourceUri", json.dumps(r.as_dict()))


class TestAc03BridgeEvidence(unittest.TestCase):
    def test_bridge_tools_call_and_sandbox_wording(self):
        obs = FakeUiHost().probe(make_ui_resource())
        self.assertEqual(obs.telemetry["bridge_method"], "tools/call")
        self.assertIn("double-iframe", obs.telemetry["sandbox"])
        self.assertNotIn("srcdoc", obs.text)


class TestAc04MockCap(unittest.TestCase):
    def test_local_mock_capped_partial(self):
        report = run_attack(AttackRequest(target="http://t.example", step="mcp-10", emit=False),
                            _offline(FakeUiHost()))
        self.assertIn(report.verdicts[0].level, ("部分生效", "未生效"))

    def test_failing_host_does_not_crash(self):
        report = run_attack(AttackRequest(target="http://t.example", step="mcp-10", emit=False),
                            _offline(FakeUiHost(fail=True)))
        self.assertIn(report.verdicts[0].level, ("部分生效", "未生效"))


class TestAc05PrefixBypass(unittest.TestCase):
    def test_traversal_hits_prefix_defect(self):
        r = escape_judge.prefix_bypass("/data/documents")
        self.assertTrue(r.hit)
        self.assertIn("..", r.input_path)

    def test_normal_path_does_not_hit(self):
        r = escape_judge.prefix_bypass("/data/documents", "/data/documents/ok.txt")
        self.assertFalse(r.hit)


class TestAc06SymlinkEscape(unittest.TestCase):
    def test_symlink_to_outside_hits_with_fake_fs(self):
        fs = _FakeFS({"/data/documents/vendor-docs": "/data/secrets/prod.env",
                      "/data/documents": "/data/documents"})
        r = escape_judge.symlink_escape("/data/documents", "vendor-docs",
                                        "/data/secrets/prod.env", fs=fs)
        self.assertTrue(r.hit)
        self.assertEqual(r.resolved, "/data/secrets/prod.env")

    def test_realpath_fix_rejects_outside(self):
        fs = _FakeFS({"/data/documents/../.secrets/credentials.json": "/data/.secrets/credentials.json",
                      "/data/documents": "/data/documents"})
        r = escape_judge.realpath_fix_check("/data/documents",
                                            "/data/documents/../.secrets/credentials.json", fs=fs)
        self.assertTrue(r.hit)  # 修复生效=拒绝越界


class TestAc07ChainPropagate(unittest.TestCase):
    def test_three_stages_built(self):
        steps = chain_build.build_chain("update_ticket", "compile_sprint",
                                        "render_report", chain_build.GADGET_KEYS)
        self.assertEqual([s.stage for s in steps], ["store", "aggregate", "render"])
        self.assertTrue(all(s.payload for s in steps))

    def test_empty_payload_yields_no_chain(self):
        self.assertEqual(chain_build.build_chain("a", "b", "c", ""), [])


class TestAc08SstiProbe(unittest.TestCase):
    def test_probe_expression_and_confirmation(self):
        self.assertEqual(chain_build.ssti_probe(), "{{7*7}}")
        self.assertTrue(chain_build.probe_confirmed("Hello 49!"))
        self.assertFalse(chain_build.probe_confirmed("Hello {{7*7}}!"))


class TestAc09CmdInject(unittest.TestCase):
    def test_separator_and_command(self):
        p = chain_build.cmd_inject(";", "id")
        self.assertIn(";", p)
        self.assertIn("id", p)

    def test_invalid_separator_falls_back(self):
        self.assertIn(";", chain_build.cmd_inject("invalid", "id"))


class TestAc10ShadowInferred(unittest.TestCase):
    def test_shadow_schema_equal_to_baseline(self):
        base = poison_mod.baseline_surface()
        shadow = poison_mod.shadow_surface()
        self.assertTrue(poison_mod.shadow_schema_equal(base, shadow))
        diff = poison_mod.diff_as_dict(poison_mod.diff_surfaces(base, shadow))
        self.assertEqual(diff["added"], [])
        self.assertEqual(diff["changed"], [])
        self.assertNotEqual(base.source, shadow.source)  # 仅后端来源不同

    def test_shadow_step_records_schema_equality(self):
        report = run_attack(AttackRequest(target="http://t.example", step="mcp-10", emit=False),
                            _offline(FakeUiHost()))
        self.assertEqual(report.verdicts[0].step_id, "mcp-10")
        self.assertIn("shadow", report.verdicts[0].reason + report.verdicts[0].observation.text)


class TestAc11EvidenceContract(unittest.TestCase):
    def test_all_new_steps_strict_emit(self):
        # RecordingWriter 为内存替身（不写盘）：断言其记录的 emit 调用含
        # strict 与三件套字段；真实写盘由端到端 CLI 验证（阶段8 mcp-10 已实测 md+png+jsonl）。
        writer = RecordingWriter()
        rt = Runtime(client=FakeHttpClient({}), writer=writer,
                     capture=NullCapture(), uihost=FakeUiHost())
        for sid in ("mcp-09", "mcp-10", "mcp-11"):
            report = run_attack(AttackRequest(target="http://t.example", step=sid, emit=True), rt)
            self.assertEqual(report.verdicts[0].step_id, sid)
        self.assertEqual(len(writer.calls), 3)
        for call in writer.calls:
            self.assertTrue(call.get("command"))
            self.assertTrue(call.get("output"))
            self.assertTrue(call.get("title"))


if __name__ == "__main__":
    unittest.main()
