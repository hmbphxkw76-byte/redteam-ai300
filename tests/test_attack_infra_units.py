#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""attack-infra 单元测试：模型 / 指纹 / 传输 / 执行 / 证据 / 截图 / 报告。

对齐规格 #213 v2：AC-01/02/03/04/05/09/10/18/23/24。全部离线，仅标准库。
"""
import json
import os
import sys
import threading
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from tools.attack_infra import fingerprint as fp  # noqa: E402
from tools.attack_infra import model, report, shot  # noqa: E402
from tools.attack_infra.command import (  # noqa: E402
    CommandResult, FakeCommand, SubprocessCommand, argv_to_text, curl_json,
)
from tools.attack_infra.evidence import EvidenceWriter, FakeEvidence  # noqa: E402
from tools.attack_infra.transport import (  # noqa: E402
    FakeTransport, HttpResponse, UrllibTransport,
)


class ModelTests(unittest.TestCase):
    def test_outcome_five_values_mutually_exclusive(self):
        self.assertEqual({o.value for o in model.Outcome},
                         {"ABSENT", "AUTH_REQUIRED", "EXPOSED_NO_AUTH",
                          "EXPLOITED", "BLOCKED"})

    def test_invalid_outcome_raises(self):
        with self.assertRaises(ValueError):
            model.Outcome("BOGUS")

    def test_step_verdict_rejects_unknown_reason(self):
        with self.assertRaises(ValueError):
            model.StepVerdict("infra-01", model.Outcome.ABSENT, reason="nope")
        with self.assertRaises(ValueError):
            model.StepVerdict("infra-99", model.Outcome.EXPLOITED)

    def test_credential_hint_never_carries_full_value(self):
        hint = model.CredentialHint(prefix="sk-", length=51, location="config.yaml:7")
        self.assertEqual(hint.as_text(), "sk-…(len=51) @ config.yaml:7")
        self.assertNotIn("sk-abc", hint.as_text())


class FingerprintTests(unittest.TestCase):
    def test_spa_fallback_is_not_a_service(self):
        """AC-03 / canonical F-13：200 + text/html 不得判为存在。"""
        resp = HttpResponse(status=200, content_type="text/html; charset=utf-8",
                            body="<!doctype html><html></html>")
        probe = fp.Probe("vllm", "/v1/models", (fp.JSON_MODELS,), (8000,))
        self.assertEqual(fp.classify(probe, resp), "")
        self.assertEqual(fp.shape_of(resp), fp.HTML)

    def test_openai_models_shape(self):
        body = json.dumps({"object": "list", "data": [{"id": "llama3.2:latest"}]})
        resp = HttpResponse(status=200, content_type="application/json", body=body)
        probe = fp.Probe("vllm", "/v1/models", (fp.JSON_MODELS,), (8000,))
        self.assertEqual(fp.classify(probe, resp), "vllm")

    def test_ollama_tags_shape(self):
        body = json.dumps({"models": [{"name": "llama3.2:latest"}]})
        resp = HttpResponse(status=200, content_type="application/json", body=body)
        probe = fp.Probe("ollama", "/api/tags", (fp.OLLAMA_TAGS,), (11434,))
        self.assertEqual(fp.classify(probe, resp), "ollama")

    def test_k8s_version_and_litellm_health(self):
        k8s = HttpResponse(status=200, content_type="application/json",
                           body=json.dumps({"gitVersion": "v1.30.0"}))
        probe = fp.Probe("k8s_apiserver", "/version", (fp.K8S_VERSION,), (6443,))
        self.assertEqual(fp.classify(probe, k8s), "k8s_apiserver")
        litellm = HttpResponse(status=200, content_type="application/json",
                               body=json.dumps({"healthy": []}))
        probe2 = fp.Probe("litellm", "/health", (fp.LITELLM_HEALTH,), (4000,))
        self.assertEqual(fp.classify(probe2, litellm), "litellm")

    def test_auth_status_and_network_error(self):
        self.assertTrue(fp.is_auth_status(HttpResponse(status=401)))
        self.assertTrue(fp.is_auth_status(HttpResponse(status=403)))
        self.assertEqual(fp.shape_of(HttpResponse(status=401)), fp.AUTH)
        self.assertEqual(fp.shape_of(HttpResponse(error="refused")), "")

    def test_target_normalisation_and_ports(self):
        self.assertEqual(fp.normalize_target("http://h:8080/x"), "h")
        self.assertEqual(fp.normalize_target("h"), "h")
        with self.assertRaises(ValueError):
            fp.normalize_target("")
        urls = [u for _, _, u in fp.probe_targets("h", (11434,))]
        self.assertIn("http://h:11434/api/tags", urls)
        self.assertNotIn("http://h:8000/v1/models", urls)

    def test_tls_scheme_for_control_plane_ports(self):
        self.assertEqual(fp.scheme_for(6443), "https")
        self.assertEqual(fp.scheme_for(10250), "https")
        self.assertEqual(fp.scheme_for(11434), "http")

    def test_triton_ready_hit(self):
        resp = HttpResponse(status=200, content_type="text/plain", body="")
        probe = fp.Probe("triton", "/v2/health/ready", (fp.EMPTY_OK,), (8000,))
        self.assertEqual(fp.classify(probe, resp), "triton")

    def test_kubelet_anonymous_ready_hit(self):
        resp = HttpResponse(status=200, content_type="text/plain", body="ok")
        probe = fp.Probe("kubelet", "/healthz", (fp.EMPTY_OK, fp.AUTH), (10250,))
        self.assertEqual(fp.classify(probe, resp), "kubelet")

    def test_kubelet_unauthorised_counts_as_auth(self):
        resp = HttpResponse(status=401, content_type="text/plain",
                            body="Unauthorized")
        self.assertEqual(fp.shape_of(resp), fp.AUTH)

    def test_six_kinds_covered(self):
        kinds = {p.kind for p in fp.PROBES}
        self.assertEqual(kinds, {"vllm", "triton", "litellm", "ollama",
                                 "k8s_apiserver", "kubelet"})


class _Handler(BaseHTTPRequestHandler):
    def do_GET(self):  # noqa: N802
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(b'{"object":"list","data":[]}')

    def log_message(self, *args):  # 静默
        return


class TransportTests(unittest.TestCase):
    def test_fake_transport_records_calls(self):
        fake = FakeTransport({"GET http://h/v1/models": HttpResponse(status=200)})
        fake.request("GET", "http://h/v1/models")
        self.assertEqual(fake.methods(), ("GET",))

    def test_urllib_transport_bypasses_env_proxy(self):
        """AC-02：环境代理存在时仍直连（否则得到代理回显，canonical F-14）。"""
        server = HTTPServer(("127.0.0.1", 0), _Handler)
        port = server.server_address[1]
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        old = {k: os.environ.get(k) for k in ("HTTP_PROXY", "http_proxy")}
        try:
            os.environ["HTTP_PROXY"] = "http://127.0.0.1:1"
            os.environ["http_proxy"] = "http://127.0.0.1:1"
            resp = UrllibTransport(timeout=5).request(
                "GET", "http://127.0.0.1:%d/v1/models" % port)
            self.assertEqual(resp.error, "")
            self.assertEqual(resp.status, 200)
            self.assertEqual(fp.shape_of(resp), fp.JSON_MODELS)
        finally:
            for key, value in old.items():
                if value is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = value
            server.shutdown()
            server.server_close()


class CommandTests(unittest.TestCase):
    def test_subprocess_runs_without_shell(self):
        result = SubprocessCommand().run(
            (sys.executable, "-c", "print('ok')"), timeout=30)
        self.assertEqual(result.code, 0)
        self.assertEqual(result.stdout.strip(), "ok")

    def test_missing_executable_maps_to_127(self):
        result = SubprocessCommand().run(("definitely-not-a-cmd-xyz",), timeout=10)
        self.assertEqual(result.code, 127)
        self.assertIn("not found", result.stderr)

    def test_fake_command_routing(self):
        fake = FakeCommand({"kubectl": CommandResult(code=0, stdout="*")})
        self.assertEqual(fake.run(("kubectl", "auth")).stdout, "*")
        self.assertEqual(fake.run(("nope",)).code, 127)

    def test_argv_rendering_and_curl_json(self):
        self.assertEqual(argv_to_text(("aws", "s3", "ls", "s3://b")),
                         "aws s3 ls s3://b")
        text = curl_json("http://h:1/api", {"model": "m", "stream": False})
        self.assertIn("-d '{\"model\": \"m\", \"stream\": false}'", text)
        self.assertNotIn("<", text)


class EvidenceTests(unittest.TestCase):
    def test_build_argv_contains_required_flags(self):
        writer = EvidenceWriter("loot/x")
        argv = writer.build_argv("infra-01", "curl x", output="o", target="h",
                                 shot_cmd="screenshot", strict=True)
        joined = " ".join(argv)
        for token in ("--step", "infra-01", "--cmd", "--out", "--strict"):
            self.assertIn(token, joined)
        self.assertTrue(writer.fragment_path("infra-01").endswith("infra-01.md"))

    def test_fake_evidence_records_without_io(self):
        fake = FakeEvidence()
        path, code, err = fake.emit("infra-02", "aws s3 ls", "out", target="h")
        self.assertEqual(code, 0)
        self.assertEqual(fake.records[0]["step_id"], "infra-02")
        self.assertTrue(path.endswith("infra-02.md"))


class ShotTests(unittest.TestCase):
    def test_plan_kinds(self):
        planner = shot.ShotPlanner("loot/shots")
        url_plan = planner.plan("infra-01", url="http://h/x")
        self.assertEqual(url_plan.kind, "url")
        transcript = planner.plan("infra-02")
        self.assertEqual(transcript.kind, "transcript")
        self.assertIn("screenshot --region infra-02", transcript.cmd)


class _ErrorHandler(BaseHTTPRequestHandler):
    def do_GET(self):  # noqa: N802
        self.send_response(404)
        self.send_header("Content-Type", "text/plain")
        self.end_headers()
        self.wfile.write(b"not found")

    def log_message(self, *args):
        return


class TransportEdgeTests(unittest.TestCase):
    def test_http_error_is_recorded_not_raised(self):
        server = HTTPServer(("127.0.0.1", 0), _ErrorHandler)
        port = server.server_address[1]
        threading.Thread(target=server.serve_forever, daemon=True).start()
        try:
            resp = UrllibTransport(timeout=5).request(
                "GET", "http://127.0.0.1:%d/x" % port)
            self.assertEqual(resp.status, 404)
            self.assertEqual(resp.body, "not found")
            self.assertIn("text/plain", resp.content_type)
        finally:
            server.shutdown()
            server.server_close()

    def test_connection_refused_is_error(self):
        resp = UrllibTransport(timeout=2).request("GET", "http://127.0.0.1:1/x")
        self.assertNotEqual(resp.error, "")
        self.assertEqual(resp.status, 0)

    def test_fake_transport_callable_and_default(self):
        fake = FakeTransport(
            {"GET http://h/a": lambda m, u, b: HttpResponse(status=201)},
            default=HttpResponse(status=204))
        self.assertEqual(fake.request("GET", "http://h/a").status, 201)
        self.assertEqual(fake.request("GET", "http://h/b").status, 204)


class EvidenceIntegrationTests(unittest.TestCase):
    """真实走通共享证据容器（AC-13 / AC-15 的端到端链路）。"""

    def test_emit_writes_fragment_with_three_pieces(self):
        import shutil
        import tempfile
        tmp = tempfile.mkdtemp(prefix="attack-infra-ev-")
        try:
            writer = EvidenceWriter(tmp)
            path, code, err = writer.emit(
                "infra-01", "curl -s --noproxy '*' http://h/x",
                output="200 application/json",
                target="h", shot_cmd="screenshot --region infra-01",
                shot_kind="transcript", note="unit", ai_log="prompt: x")
            self.assertEqual(code, 0, err)
            with open(path, encoding="utf-8") as handle:
                text = handle.read()
            self.assertIn("### 步骤 infra-01", text)
            self.assertIn("确切命令", text)
            self.assertIn("| 截图 | 是 | 已提供 |", text)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


class ReportTests(unittest.TestCase):

    def _report(self):
        rep = model.RunReport(target="h")
        rep.steps.append(model.StepVerdict("infra-01", model.Outcome.EXPOSED_NO_AUTH,
                                           summary="hit", command="curl -s x"))
        rep.steps.append(model.StepVerdict("infra-02", model.Outcome.ABSENT,
                                           reason="none_found", summary="none",
                                           command="aws s3 ls --no-sign-request"))
        return rep

    def test_summary_counts(self):
        self.assertIn("exposed_no_auth=1", report.summary(self._report()))

    def test_render_lists_next_skills_and_no_placeholders(self):
        text = report.render(self._report())
        self.assertIn("attack-mcp-tool", text)
        self.assertNotIn("<bucket>", text)
        for line in text.splitlines():
            if line.startswith("curl ") or line.startswith("aws "):
                self.assertNotIn("<", line)

    def test_json_round_trip(self):
        payload = json.loads(report.to_json(self._report()))
        self.assertEqual(len(payload["steps"]), 2)
        self.assertEqual(payload["steps"][1]["outcome"], "ABSENT")

    def test_exit_code_reflects_blocking(self):
        rep = self._report()
        self.assertEqual(report.exit_code(rep), 0)
        rep.steps.append(model.StepVerdict("infra-08", model.Outcome.BLOCKED,
                                           reason="mismatch"))
        self.assertEqual(report.exit_code(rep), 1)


if __name__ == "__main__":
    unittest.main()


class InventoryTests(unittest.TestCase):
    """SKILL.md 前置第 1 条：复用 recon-ai 资产清单。"""

    def setUp(self):
        import tempfile
        self.dir = tempfile.mkdtemp(prefix="attack-infra-inv-")

    def tearDown(self):
        import shutil
        shutil.rmtree(self.dir, ignore_errors=True)

    def _write(self, payload):
        import json as _json
        path = os.path.join(self.dir, "inventory.json")
        with open(path, "w", encoding="utf-8") as handle:
            _json.dump(payload, handle)
        return path

    def test_extracts_urls_and_host_port_pairs(self):
        from tools.attack_infra import inventory
        path = self._write({"assets": [
            {"endpoint": "http://10.0.0.5:11434", "host": "10.0.0.5", "port": 6443},
            {"note": "见 10.0.0.9:8000 的模型服务"},
        ]})
        endpoints = inventory.load_endpoints(path)
        self.assertIn("http://10.0.0.5:11434", endpoints)
        self.assertIn("10.0.0.5:6443", endpoints)
        self.assertIn("10.0.0.9:8000", endpoints)

    def test_missing_or_invalid_file_yields_empty(self):
        from tools.attack_infra import inventory
        self.assertEqual(inventory.load_endpoints(""), ())
        bad = os.path.join(self.dir, "bad.json")
        with open(bad, "w", encoding="utf-8") as handle:
            handle.write("{not json")
        self.assertEqual(inventory.load_endpoints(bad), ())

    def test_host_ports_dedupes_and_parses(self):
        from tools.attack_infra import inventory
        pairs = inventory.host_ports(["http://h:11434/x", "h:11434", "h:8000"])
        self.assertEqual(pairs, (("h", 11434), ("h", 8000)))


class BeforeAfterReportTests(unittest.TestCase):
    """SKILL.md 质量门：部署/权限 before/after。"""

    def _step(self, sid, outcome, findings=None, summary="", reason=""):
        return model.StepVerdict(sid, outcome, summary=summary, reason=reason,
                                 findings=findings or [])

    def test_section_lists_baseline_and_post_state(self):
        finding = model.Finding(
            endpoint=model.Endpoint(url="http://h:11434/v1/models",
                                    port=11434, kind="ollama", status=200),
            outcome=model.Outcome.EXPOSED_NO_AUTH)
        rep = model.RunReport(target="h", steps=[
            self._step("infra-01", model.Outcome.EXPOSED_NO_AUTH, [finding]),
            self._step("infra-06", model.Outcome.EXPLOITED, summary="取得执行回显"),
        ])
        text = report.render(rep)
        self.assertIn("利用前后对照", text)
        self.assertIn("利用前（基线）", text)
        self.assertIn("利用后（infra-06）", text)

    def test_section_states_absence_honestly(self):
        finding = model.Finding(
            endpoint=model.Endpoint(url="http://h:11434/api/tags",
                                    port=11434, kind="ollama", status=200),
            outcome=model.Outcome.EXPOSED_NO_AUTH)
        rep = model.RunReport(target="h", steps=[
            self._step("infra-01", model.Outcome.EXPOSED_NO_AUTH, [finding]),
            self._step("infra-06", model.Outcome.ABSENT, reason="none_found",
                       summary="无入口"),
        ])
        self.assertIn("未取得利用后状态", report.render(rep))


class SkillClauseTests(unittest.TestCase):
    """SKILL.md 条款补齐：脚本来源、截图目标标识与时间戳。"""

    def test_provenance_covers_exactly_five_demo_script_steps(self):
        from tools.attack_infra import provenance
        step_ids = {"infra-02", "infra-03", "infra-04", "infra-05", "infra-06"}
        self.assertEqual(set(provenance.SCRIPT_SOURCES), step_ids)
        for sid in step_ids:
            fields = provenance.provenance(sid)
            self.assertTrue(fields["script_src"].startswith("https://"))
            self.assertTrue(fields["script_note"].strip())
        self.assertIsNone(provenance.provenance("infra-01"))

    def test_evidence_argv_carries_script_source(self):
        writer = EvidenceWriter("loot/x")
        argv = writer.build_argv("infra-02", "aws s3 ls",
                                 script_src="https://example.test/ref",
                                 script_note="adapted")
        self.assertIn("--script-src", argv)
        self.assertIn("--script-note", argv)

    def test_shot_hook_carries_target_and_timestamp(self):
        plan = shot.ShotPlanner("loot/shots").plan(
            "infra-01", target="192.0.2.5", timestamp="2026-11-15T15:00:00+0800")
        self.assertIn("--target 192.0.2.5", plan.cmd)
        self.assertIn("--timestamp 2026-11-15T15:00:00+0800", plan.cmd)
