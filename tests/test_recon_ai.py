#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""recon-ai 验收条件测试（S2）：每条 AC 一组断言，只测外部行为。

覆盖：AC-01..AC-23（AC-24 端到端为实跑留痕，AC-25 为 S0 套件本身）。
依赖：仅标准库；网络经 `FakeTransport` 替身，截图经 `FakeShot` 替身 → 零外网。
"""
import json
import os
import re
import subprocess
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from tools.recon_ai import inventory, policy, probes, runner  # noqa: E402
from tools.recon_ai import evidence as evidence_mod  # noqa: E402
from tools.recon_ai import shot as shot_mod  # noqa: E402
from tools.recon_ai.model import (Asset, AssetInventory, Category, Existence,  # noqa: E402
                                  ProbeResult, credential_hint)
from tools.recon_ai.transport import FakeTransport, HttpResponse  # noqa: E402

COLLECT = os.path.join(ROOT, "tools", "collect_evidence.py")
TARGET = "http://t"
SSE_OK = ('event: meta\ndata: {"request_id": "r-001", "lab_id": "MM_04", '
          '"phase": 3, "control_mode": "off", "artifact_replay": true}\n\n'
          'data: {"content": "RECON-PROBE-OK"}\n\n')
SSE_REFUSE = ('event: meta\ndata: {"request_id": "r-002", "lab_id": "MM_04", '
              '"phase": 3, "control_mode": "on"}\n\n'
              'data: {"content": "I can\'t help with that."}\n\n')
CONFIG = ('{"training_labs_enabled":false,"training_lab_ids":["MM_04"],'
          '"llm_model_default":"LongCat-2.5"}')
JSON404 = '{"detail":"Not Found"}'
HTML_FALLBACK = "<!doctype html><html><body><div id='root'></div></body></html>"


def base_routes(sse=SSE_OK, config=CONFIG, fallback=HTML_FALLBACK,
                rag_trace="var retrieved_knowledge=1;", oracle='{"success":false,"message":"Nope."}'):
    """构造与演练目标同构的替身路由（确定性）。"""
    return {
        ("GET", TARGET + "/api/config"):
            HttpResponse(200, config, {"Server": "nginx/1.27.5"}, "application/json"),
        ("GET", TARGET + "/v1/models"):
            HttpResponse(200, fallback, {}, "text/html"),
        ("POST", TARGET + "/api/labs/MM_04/chat"):
            HttpResponse(200, sse, {"set-cookie": "aivp_sid=x"}, "text/event-stream"),
        ("GET", TARGET + "/api/me/runs?limit=1"):
            HttpResponse(200, '{"runs":[]}', {}, "application/json"),
        ("GET", TARGET + "/explore"):
            HttpResponse(200, '<!doctype html><script src="/assets/index-abc.js"></script>',
                         {}, "text/html"),
        ("GET", TARGET + "/assets/index-abc.js"):
            HttpResponse(200, rag_trace, {}, "application/javascript"),
        ("GET", TARGET + "/api/labs/MM_05/summary"):
            HttpResponse(422, '{"detail":[{"loc":["query","request_id"]}]}',
                         {}, "application/json"),
        ("GET", TARGET + "/api/labs/DE_01/summary"):
            HttpResponse(422, '{"detail":[{"loc":["query","request_id"],"msg":"required"}]}',
                         {}, "application/json"),
        ("POST", TARGET + "/api/secrets/validate"):
            HttpResponse(200, oracle, {}, "application/json"),
        ("GET", TARGET + "/api/labs/MCP_01/summary"):
            HttpResponse(422, '{"detail":[{"loc":["query","request_id"]}]}',
                         {}, "application/json"),
    }


def run_fake(tmp, routes=None, profile="passive", capture=True):
    """以替身执行一次完整侦察，返回 RunReport。"""
    writer = evidence_mod.EvidenceWriter(tmp, manifest=os.path.join(tmp, "MANIFEST.jsonl"))
    return runner.run_recon(
        target=TARGET, profile=profile, lab="MM_04", out_dir=tmp,
        transport=FakeTransport(routes or base_routes()), shot=shot_mod.FakeShot(),
        writer=writer, capture_shots=capture,
    )


class ProfileAndHeaderTests(unittest.TestCase):
    """AC-01 / AC-02 / AC-03：执行分级与报告头。"""

    def test_ac01_passive_is_default_and_has_no_active_ports(self):
        self.assertEqual(policy.normalize_profile(None), "passive")
        spec = probes.find("recon-04")
        passive = policy.gate_requests(spec, "passive")
        self.assertEqual([r for r in passive if r.tag == "port-probe"], [],
                         "被动档不得包含端口探测请求")
        with tempfile.TemporaryDirectory() as tmp:
            report = run_fake(tmp)
            with open(report.evidence_paths[0], encoding="utf-8") as f:
                self.assertIn("**执行分级**：`passive`", f.read())

    def test_ac02_active_adds_bounded_port_probes(self):
        spec = probes.find("recon-04")
        active = [r for r in policy.gate_requests(spec, "active") if r.tag == "port-probe"]
        self.assertTrue(active, "主动档应追加端口探测")
        self.assertLessEqual(len(active), policy.MAX_ACTIVE_PORTS,
                             "主动端口数须受上限约束（禁止全端口扫描）")

    def test_ac03_report_header_carries_target_profile_timestamp(self):
        with tempfile.TemporaryDirectory() as tmp:
            report = run_fake(tmp)
            with open(report.evidence_paths[0], encoding="utf-8") as f:
                text = f.read()
            with open(report.inventory_json, encoding="utf-8") as f:
                data = json.load(f)
        for token in ("`%s`" % TARGET, "**执行分级**：`passive`", "**时间戳**：`"):
            self.assertIn(token, text)
        self.assertTrue(data["timestamp"])
        self.assertEqual(data["timestamp"], data["generated_at"])


class ExistenceTests(unittest.TestCase):
    """AC-04..AC-12：存在性三值与七类组件判据。"""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = self._tmp.name
        self.report = run_fake(self.tmp)

    def tearDown(self):
        self._tmp.cleanup()

    def _judge(self, step_id):
        return self.report.judgements[step_id]

    def test_ac04_spa_fallback_is_absent_not_present(self):
        fallback = HttpResponse(200, HTML_FALLBACK, {}, "text/html")
        self.assertTrue(probes.is_spa_fallback(fallback))
        self.assertFalse(probes.is_spa_fallback(
            HttpResponse(200, '{"a":1}', {}, "application/json")))
        # 探测级三值：回退页 → 不存在；JSON → 存在；超时 → 不可判定
        self.assertEqual(self.report.results["recon-01"][1].existence, Existence.ABSENT)
        self.assertEqual(self.report.results["recon-01"][0].existence, Existence.PRESENT)
        self.assertEqual(self._judge("recon-01").existence, Existence.PRESENT)
        dead = ProbeResult(step_id="recon-01", url="u", error="timed out")
        judgement = probes.judge_engine([dead, None], {"profile": "passive"})
        self.assertEqual(judgement.existence, Existence.UNDETERMINED)

    def test_ac05_model_name_enters_inventory(self):
        asset = [a for a in self.report.inventory.assets if a.category == "LLM引擎"][0]
        self.assertIn("LongCat-2.5", asset.product)
        self.assertTrue(asset.version)

    def test_ac06_fallback_catalog_does_not_add_asset(self):
        steps = [a.evidence_step for a in self.report.inventory.assets]
        self.assertEqual(steps.count("recon-01"), 1,
                         "/v1/models 回退不得新增资产条目")

    def test_ac07_model_service_records_sse_metadata(self):
        note = self._judge("recon-02").note
        self.assertIn("SSE 事件类型", note)
        self.assertIn("request_id", note)
        self.assertIn("SSE", self._judge("recon-02").product)

    def test_ac08_rag_present_with_traces_and_undetermined_without(self):
        self.assertEqual(self._judge("recon-03").existence, Existence.PRESENT)
        bare = runner.run_recon(
            target=TARGET, out_dir=os.path.join(self.tmp, "bare"),
            transport=FakeTransport(base_routes(rag_trace="var nothing=1;")),
            shot=shot_mod.FakeShot(),
            writer=evidence_mod.EvidenceWriter(os.path.join(self.tmp, "bare")),
            capture_shots=True)
        self.assertEqual(bare.judgements["recon-03"].existence, Existence.UNDETERMINED)

    def test_ac09_vector_undetermined_in_passive(self):
        self.assertEqual(self._judge("recon-04").existence, Existence.UNDETERMINED)
        self.assertIn("向量库", self.report.inventory.undetermined)

    def test_ac10_agent_phase_recorded(self):
        self.assertEqual(self._judge("recon-05").existence, Existence.PRESENT)
        self.assertIn("request_id", self._judge("recon-05").note)
        phases = [a.phase for a in self.report.inventory.assets if a.phase]
        self.assertIn("3", phases, "清单须携带编排阶段（来自 recon-02 的 SSE meta）")
        self.assertIn("推断", self._judge("recon-05").product)

    def test_ac11_mcp_records_200_plus_success_false(self):
        note = self._judge("recon-06").note
        self.assertIn("200", note)
        self.assertIn("success:false", note)

    def test_ac12_guardrail_echo_vs_refusal(self):
        self.assertIn("放行原样回显", self._judge("recon-07").signature)
        refuse = runner.run_recon(
            target=TARGET, out_dir=os.path.join(self.tmp, "refuse"),
            transport=FakeTransport(base_routes(sse=SSE_REFUSE)),
            shot=shot_mod.FakeShot(),
            writer=evidence_mod.EvidenceWriter(os.path.join(self.tmp, "refuse")),
            capture_shots=True)
        self.assertIn("拒答", refuse.judgements["recon-07"].signature)


class InventoryContractTests(unittest.TestCase):
    """AC-13 / AC-14 / AC-15：清单契约、双态输出、凭据指纹。"""

    def test_ac13_missing_field_breaks_contract(self):
        bad = Asset("", "", "", "", "", "", "")
        inv = AssetInventory.create(target="t", profile="passive", assets=[bad])
        self.assertTrue(inv.contract_violations())
        good = Asset("ai-llm-h-01", "LLM引擎", "LongCat-2.5", "2.5",
                     "http://h/api/config", "无", "recon-01")
        clean = AssetInventory.create(target="t", profile="passive", assets=[good])
        self.assertEqual(clean.contract_violations(), [])

    def test_ac14_dual_format_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            report = run_fake(tmp)
            with open(report.inventory_json, encoding="utf-8") as f:
                data = json.load(f)
            self.assertIn("assets", data)
            self.assertEqual(len(data["assets"]), len(report.inventory.assets))
            with open(report.inventory_md, encoding="utf-8") as f:
                self.assertIn("| 资产ID |", f.read())
            self.assertTrue(os.path.isfile(report.report_md))

    def test_ac15_no_plaintext_credentials(self):
        hint = credential_hint("sk-super-secret-value")
        self.assertTrue(hint.startswith("Bearer-"))
        self.assertNotIn("sk-super-secret-value", hint)
        with tempfile.TemporaryDirectory() as tmp:
            report = run_fake(tmp)
            for path in report.evidence_paths + [report.inventory_md, report.report_md]:
                with open(path, encoding="utf-8") as f:
                    text = f.read()
                # 明文凭据特征：真实 Bearer 值、sk- 密钥、cookie 原值
                self.assertIsNone(re.search(r"Bearer\s+(?!<)[A-Za-z0-9]{12,}", text))
                self.assertIsNone(re.search(r"sk-[A-Za-z0-9]{12,}", text))
                self.assertIsNone(re.search(r"aivp_sid=[0-9a-f-]{8,}", text))
            # 会话 cookie 应被压缩为指纹而非原值
            model_asset = [a for a in report.inventory.assets
                           if a.category == "模型服务"][0]
            self.assertTrue(model_asset.credential_hint.startswith("Bearer-"))


class EvidenceQualityTests(unittest.TestCase):
    """AC-16..AC-20：证据三件套、脚本来源、flag 双通道、清单、严格模式。"""

    def test_ai_log_only_for_steps_that_prompt_the_model(self):
        """§6.3 真实性：未发送提示的步骤不得出现 AI 交互日志（禁止跨步错归属）。"""
        with tempfile.TemporaryDirectory() as tmp:
            report = run_fake(tmp)
            for path in report.evidence_paths:
                name = os.path.basename(path)
                with open(path, encoding="utf-8") as f:
                    text = f.read()
                has_log = "#### AI 交互日志" in text
                if name in ("recon-02.md", "recon-07.md"):
                    self.assertTrue(has_log, "%s 应记录模型交互" % name)
                else:
                    self.assertFalse(has_log, "%s 未发送提示，不得臆造 AI 交互日志" % name)

    def test_ac16_fragments_have_three_required_sections(self):
        with tempfile.TemporaryDirectory() as tmp:
            report = run_fake(tmp)
            self.assertGreaterEqual(len(report.evidence_paths), 7)
            for path in report.evidence_paths:
                with open(path, encoding="utf-8") as f:
                    text = f.read()
                for label in ("确切命令", "关键输出", "截图（访问证明）"):
                    self.assertIn(label, text, "%s 缺 %s" % (path, label))
                self.assertIn("**三件套齐全**：是。", text)

    def _collect(self, *args, stdin=""):
        return subprocess.run([sys.executable, COLLECT] + list(args),
                              input=stdin, capture_output=True, text=True,
                              encoding="utf-8")

    def test_ac17_script_section_both_states(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = os.path.join(tmp, "f.md")
            self._collect("--step", "s1", "--cmd", "id", "--out", out,
                          "--output", "uid=0", "--shot-cmd", "shot hook")
            with open(out, encoding="utf-8") as f:
                self.assertIn("未使用脚本", f.read())
            script = os.path.join(tmp, "x.py")
            with open(script, "w", encoding="utf-8") as f:
                f.write("print(1)\n")
            self._collect("--step", "s2", "--cmd", "python x.py", "--out", out,
                          "--output", "1", "--shot-cmd", "shot hook",
                          "--script", script, "--script-src", "https://example.com/x.py",
                          "--script-note", "未修改")
            with open(out, encoding="utf-8") as f:
                text = f.read()
            self.assertIn("https://example.com/x.py", text)
            self.assertIn("sha256:", text)
            self.assertIn("未修改", text)

    def test_ac18_flag_dual_channel_consistency(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = os.path.join(tmp, "f.md")
            self._collect("--step", "s1", "--cmd", "cat ai_vector.txt", "--out", out,
                          "--output", "FLAG-1", "--shot-cmd", "hook",
                          "--flag-panel", "FLAG-1", "--flag-shot", "FLAG-1")
            with open(out, encoding="utf-8") as f:
                self.assertIn("**一致**", f.read())
            r = self._collect("--step", "s2", "--cmd", "cat ai_vector.txt", "--out", out,
                              "--output", "FLAG-1", "--shot-cmd", "hook",
                              "--flag-panel", "FLAG-1", "--flag-shot", "FLAG-2")
            self.assertIn("不一致", r.stdout + r.stderr)

    def test_ac19_manifest_jsonl_fields(self):
        with tempfile.TemporaryDirectory() as tmp:
            manifest = os.path.join(tmp, "m.jsonl")
            out = os.path.join(tmp, "f.md")
            self._collect("--step", "recon-01", "--cmd", "curl -s t/api/config",
                          "--out", out, "--output", "{}", "--shot-cmd", "hook",
                          "--profile", "passive", "--manifest", manifest,
                          "--retention", "evidence/m.md")
            record = evidence_mod.load_manifest(manifest)[0]
            for key in ("step_id", "command", "sha256", "timestamp",
                        "profile", "retention", "pieces"):
                self.assertIn(key, record)
            self.assertEqual(record["profile"], "passive")
            self.assertEqual(len(record["sha256"]), 64)

    def test_ac20_strict_fails_on_gap_or_inconsistency(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = os.path.join(tmp, "f.md")
            gap = self._collect("--step", "s1", "--cmd", "id", "--out", out, "--strict")
            self.assertEqual(gap.returncode, 1)
            inconsistent = self._collect(
                "--step", "s2", "--cmd", "id", "--out", out, "--output", "x",
                "--shot-cmd", "hook", "--flag-panel", "A", "--flag-shot", "B", "--strict")
            self.assertEqual(inconsistent.returncode, 1)

    def test_runner_emits_strict_clean_evidence(self):
        with tempfile.TemporaryDirectory() as tmp:
            report = run_fake(tmp)
        self.assertEqual(report.warnings, [], "默认路径不应产生证据质量门告警")


class DownstreamContractTests(unittest.TestCase):
    """H1/H2 回归：证据格式必须仍可被 report-exam 解析；质量门失败须显式。"""

    def test_flag_fragment_reparsed_by_report_exam(self):
        from report_exam.index import parse_fragment
        with tempfile.TemporaryDirectory() as tmp:
            out = os.path.join(tmp, "f.md")
            subprocess.run(
                [sys.executable, COLLECT, "--step", "recon-07", "--cmd", "cat ai_vector.txt",
                 "--out", out, "--output", "uid=0", "--shot-cmd", "hook",
                 "--flag-panel", "FLAG-A", "--flag-shot", "FLAG-A"],
                check=True, capture_output=True)
            with open(out, encoding="utf-8") as f:
                frag = parse_fragment(f.read(), out)
        self.assertEqual(frag.flag, "FLAG-A", "flag 段须保留可解析的 fenced 原值")
        self.assertEqual(frag.command, "cat ai_vector.txt")

    def test_missing_screenshot_surfaces_as_quality_failure(self):
        with tempfile.TemporaryDirectory() as tmp:
            report = runner.run_recon(
                target=TARGET, out_dir=tmp, transport=FakeTransport(base_routes()),
                shot=shot_mod.NullShot(), writer=evidence_mod.EvidenceWriter(tmp),
                capture_shots=True)
        self.assertTrue(report.quality_failures,
                        "缺截图须显式记为质量门失败（C8 不得静默）")


class PolicyTests(unittest.TestCase):
    """AC-21 / AC-22：诱饵判定与失败隔离。"""

    def test_ac21_decoy_flag_with_basis(self):
        empty = inventory.build({}, TARGET, "passive")
        self.assertTrue(empty.decoy_suspected)
        self.assertIn("0/7", empty.decoy_reason)
        self.assertEqual(empty.timebox_minutes, 30)

    def test_ac22_single_step_failure_is_isolated(self):
        original = probes.JUDGES["rag"]

        def boom(results, ctx):
            raise RuntimeError("模拟单面失败")

        probes.JUDGES["rag"] = boom
        try:
            with tempfile.TemporaryDirectory() as tmp:
                report = run_fake(tmp)
                self.assertTrue(os.path.isfile(report.report_md),
                                "验证报告须在失败隔离下仍产出")
        finally:
            probes.JUDGES["rag"] = original
        self.assertIn("recon-03", report.failed_steps)
        self.assertGreaterEqual(len(report.evidence_paths), 6,
                                "其余步骤仍须产出证据（失败隔离）")


class CodeHygieneTests(unittest.TestCase):
    """AC-23：零第三方依赖。"""

    def test_ac23_no_third_party_imports(self):
        """以标准库名单反向判定：任何非标准库顶层模块即违规（不依赖黑名单）。"""
        pkg = os.path.join(ROOT, "tools", "recon_ai")
        allowed = set(sys.stdlib_module_names) | {"tools", "report_exam"}
        for name in sorted(os.listdir(pkg)):
            if not name.endswith(".py") or name == "__init__.py":
                continue
            with open(os.path.join(pkg, name), encoding="utf-8") as f:
                for line in f:
                    stripped = line.strip()
                    if stripped.startswith("from ."):
                        continue
                    if stripped.startswith("import "):
                        mods = [m.split(" ")[0].split(".")[0]
                                for m in stripped[7:].split(",")]
                    elif stripped.startswith("from "):
                        mods = [stripped[5:].split(" ")[0].split(".")[0]]
                    else:
                        continue
                    for mod in mods:
                        self.assertIn(mod, allowed,
                                      "%s 引入了非标准库依赖 %s" % (name, mod))


if __name__ == "__main__":
    unittest.main()
