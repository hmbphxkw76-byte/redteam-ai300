#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Ch9 扩展测试（AC-01..AC-20）。

只断言外部行为：ctx → 结论/outcome/reason/命令/证据字段。
全部离线（FakeCommand/FakeTransport），不发真实网络请求。
"""
import base64
import json
import sys
import unittest

from tests._paths import ROOT  # noqa: E402
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from tools.attack_infra import ch9_container, ch9_gpu, ch9_iam, ch9_k8s  # noqa: E402
from tools.attack_infra import ch9_runner, ch9_scope, ch9_secrets  # noqa: E402
from tools.attack_infra.ch9_model import (  # noqa: E402
    ABSENT, AUTH_REQUIRED, BLOCKED, EXPLOITED, EXPOSED_NO_AUTH,
    Capability, Ch9Verdict, CredFingerprint,
)
from tools.attack_infra.command import CommandResult, FakeCommand  # noqa: E402
from tools.attack_infra.evidence import FakeEvidence  # noqa: E402
from tools.attack_infra.model import RunContext  # noqa: E402
from tools.attack_infra.transport import FakeTransport, HttpResponse  # noqa: E402


def _ctx(command=None, transport=None, **kwargs):
    base = dict(target="h", transport=transport or FakeTransport({}),
                command=command or FakeCommand({}), timeout=5)
    base.update(kwargs)
    return RunContext(**base)


def _jwt(sub):
    payload = base64.urlsafe_b64encode(json.dumps({"sub": sub}).encode()).decode().rstrip("=")
    return "hdr." + payload + ".sig"


class Ch9ModelTests(unittest.TestCase):
    def test_ac19_reason_enum_enforced(self):
        with self.assertRaises(ValueError):
            Ch9Verdict("ch9-x", BLOCKED, reason="bogus_reason")
        v = Ch9Verdict("ch9-x", ABSENT, reason="no_tool")
        self.assertEqual(v.reason, "no_tool")


class IamTests(unittest.TestCase):
    def test_ac01_parse_statement_fields(self):
        doc = json.dumps({"PolicyDocument": {"Statement": [{
            "Sid": "S", "Effect": "Allow", "Action": ["s3:Get*"],
            "Resource": "*", "Condition": {"StringEquals": {"k": "v"}},
        }]}})
        parsed = ch9_iam.enumerate_policies(doc)
        self.assertEqual(parsed[0]["sid"], "S")
        self.assertEqual(parsed[0]["actions"], ["s3:Get*"])
        self.assertEqual(parsed[0]["condition"], {"StringEquals": {"k": "v"}})

    def test_ac02_trust_root_principal_allows(self):
        trust = json.dumps({"AssumeRolePolicyDocument": {"Statement": [{
            "Effect": "Allow", "Action": "sts:AssumeRole",
            "Principal": {"AWS": "arn:aws:iam::123:root"},
        }]}})
        cmd = FakeCommand({"aws": CommandResult(code=0, stdout=trust)})
        v = ch9_iam.trust_step(_ctx(cmd, iam_role="MLOpsRole",
                                    iam_principal="arn:aws:iam::123:role/A"))
        self.assertIs(v.outcome, EXPOSED_NO_AUTH)
        self.assertTrue(v.evidence_extra["trust_allows"])
        self.assertTrue(v.command and v.output)

    def test_ac02_trust_explicit_deny(self):
        trust = json.dumps({"Statement": [{
            "Effect": "Deny", "Action": "sts:AssumeRole",
            "Principal": {"AWS": "arn:aws:iam::123:role/A"},
        }]})
        cmd = FakeCommand({"aws": CommandResult(code=0, stdout=trust)})
        v = ch9_iam.trust_step(_ctx(cmd, iam_role="MLOpsRole",
                                    iam_principal="arn:aws:iam::123:role/A"))
        self.assertIs(v.outcome, BLOCKED)
        self.assertFalse(v.evidence_extra["trust_allows"])

    def test_ac03_fingerprint_no_plaintext(self):
        fp = CredFingerprint(prefix="ASIA", length=20, location="hop-1:AccessKeyId")
        self.assertIn("ASIA", fp.as_text())
        self.assertNotIn("SECRETVALUE", fp.as_text())

    def test_ac04_chain_crosses_boundary(self):
        out = json.dumps({"Credentials": {"AccessKeyId": "ASIAEXAMPLE",
                                          "SecretAccessKey": "SECRETEXAMPLE",
                                          "SessionToken": "TOKENEXAMPLE"},
                          "PolicyDocument": {"Statement": [
                              {"Action": "*", "Resource": "*"}]}})
        cmd = FakeCommand({"aws": CommandResult(code=0, stdout=out)})
        v = ch9_iam.chain_verdict(_ctx(cmd, iam_chain=("arn:aws:iam::1:role/A",)))
        self.assertIs(v.outcome, EXPLOITED)
        self.assertTrue(v.evidence_extra["crossed_boundary"])
        self.assertIn("项目边界", v.summary)
        self.assertNotIn("SECRETEXAMPLE", v.output)

    def test_ac19_chain_blocked(self):
        cmd = FakeCommand({"aws": CommandResult(code=1, stderr="AccessDenied")})
        v = ch9_iam.chain_verdict(_ctx(cmd, iam_chain=("arn:aws:iam::1:role/A",)))
        self.assertIs(v.outcome, BLOCKED)


class K8sTests(unittest.TestCase):
    def test_ac05_raw_api_url(self):
        v = ch9_k8s.token_surface(_ctx(k8s_api_host="cp-01", k8s_api_port="6443"))
        self.assertIs(v.outcome, EXPOSED_NO_AUTH)
        self.assertIn("/apis/authorization.k8s.io/v1/selfsubjectrulesreviews",
                      v.evidence_extra["api_url"])

    def test_ac05_absent_without_host(self):
        v = ch9_k8s.token_surface(_ctx())
        self.assertIs(v.outcome, ABSENT)

    def test_ac06_same_rules_clusterrole(self):
        rules = [{"verbs": ["get", "list"], "resources": ["secrets"], "apiGroups": [""]}]
        body = json.dumps({"status": {"resourceRules": rules}})
        url = "https://k8s" + ch9_k8s.RULES_PATH
        tr = FakeTransport({"POST " + url: HttpResponse(
            status=200, body=body, content_type="application/json")})
        v = ch9_k8s.same_rules_across_ns(_ctx(transport=tr, k8s_rules_url=url))
        self.assertIs(v.outcome, EXPOSED_NO_AUTH)
        self.assertTrue(v.evidence_extra["same_rules"])

    def test_ac07_jwt_subject(self):
        sub = "system:serviceaccount:pipeline-system:argo-workflow-controller"
        self.assertEqual(ch9_k8s.jwt_subject(_jwt(sub)), sub)

    def test_ac08_capability_matrix_completes(self):
        a = (Capability("secrets", "list"),)
        b = (Capability("pods", "create"),)
        v = ch9_k8s.capability_matrix(_ctx(identity_a_rules=a, identity_b_rules=b))
        self.assertIs(v.outcome, EXPLOITED)
        self.assertTrue(v.evidence_extra["completes"])

    def test_ac08_matrix_gap(self):
        a = (Capability("pods", "get"),)
        v = ch9_k8s.capability_matrix(_ctx(identity_a_rules=a))
        self.assertIs(v.outcome, BLOCKED)
        self.assertIn("no_secret_read", v.evidence_extra["gap"])


class SecretsTests(unittest.TestCase):
    def test_ac09_five_service_fingerprints(self):
        text = "AKIAEXAMPLEKEY123456 key=sk-testFAKE1234567890 postgres://u:p@h/db"
        cmd = FakeCommand({"aws": CommandResult(code=0, stdout=text)})
        v = ch9_secrets.hunt_services(_ctx(cmd))
        self.assertEqual(v.evidence_extra["service_count"], 5)
        blob = json.dumps(v.evidence_extra["fingerprint_groups"], ensure_ascii=False)
        self.assertNotIn("AKIAEXAMPLEKEY123456", blob)

    def test_ac09_all_denied(self):
        cmd = FakeCommand({"aws": CommandResult(code=1, stderr="AccessDenied")})
        v = ch9_secrets.hunt_services(_ctx(cmd))
        self.assertIs(v.outcome, AUTH_REQUIRED)

    def test_ac10_ssm_old_password(self):
        doc = json.dumps({"Parameters": [
            {"Value": "postgresql://u:old@h/db"}, {"Value": "postgresql://u:new@h/db"}]})
        cmd = FakeCommand({"aws": CommandResult(code=0, stdout=doc)})
        v = ch9_secrets.ssm_old_password(_ctx(cmd))
        self.assertTrue(v.evidence_extra["has_old_password"])
        self.assertNotIn("old", v.output)

    def test_ac11_filter_hits_only(self):
        cmd = FakeCommand({"aws": CommandResult(code=0, stdout="INFO start\n[DEBUG] api key: sk-x\nINFO done")})
        v = ch9_secrets.filter_log_hits(_ctx(cmd))
        self.assertEqual(v.evidence_extra["hit_count"], 1)
        self.assertNotIn("INFO start", v.output)

    def test_ac09_bare_secret_value_never_in_output(self):
        """P-2 回归：裸 SecretString / token 值不得落进证据 output。"""
        leak = "my-api-key-SECRET123456"
        for stdout in ('{"SecretString": "%s"}' % leak,
                       'api_key=%s' % leak,
                       '[DEBUG] token %s' % leak):
            with self.subTest(stdout=stdout):
                cmd = FakeCommand({"aws": CommandResult(code=0, stdout=stdout)})
                v = ch9_secrets.hunt_services(_ctx(cmd))
                self.assertNotIn(leak, v.output)
                v2 = ch9_secrets.ssm_old_password(_ctx(cmd))
                self.assertNotIn(leak, v2.output)
                v3 = ch9_secrets.filter_log_hits(_ctx(cmd))
                self.assertNotIn(leak, v3.output)


class ContainerTests(unittest.TestCase):
    def test_ac12_writable_shared_volume(self):
        pod = json.dumps({"spec": {
            "containers": [
                {"name": "pre", "volumeMounts": [{"name": "queue", "readOnly": False}]},
                {"name": "inf", "volumeMounts": [{"name": "queue", "readOnly": False}]},
            ], "volumes": [{"name": "queue"}]}})
        v = ch9_container.writable_shared_volume(_ctx(pod_json=pod, can_exec_sidecar=True))
        self.assertIs(v.outcome, EXPOSED_NO_AUTH)
        self.assertIn("queue", v.evidence_extra["writable_volumes"])

    def test_ac12_read_only_absent(self):
        pod = json.dumps({"spec": {"containers": [
            {"name": "pre", "volumeMounts": [{"name": "q", "readOnly": True}]}]}})
        v = ch9_container.writable_shared_volume(_ctx(pod_json=pod))
        self.assertIs(v.outcome, ABSENT)

    def test_ac13_intercept_ai_log(self):
        v = ch9_container.intercept_verdict(_ctx(
            inference_before="critical", inference_after="routine",
            inference_prompt="classify"))
        self.assertTrue(v.evidence_extra["changed"])
        self.assertIn("before", v.evidence_extra["ai_log"])


class ScopeOpsecTests(unittest.TestCase):
    def test_ac14_out_of_scope_active_blocked(self):
        v = ch9_scope.scope_gate(_ctx(discovered_resource="rainyday",
                                      out_of_scope=True, active_action=True))
        self.assertIs(v.outcome, BLOCKED)
        self.assertEqual(v.reason, "forbidden")

    def test_ac15_active_default_off(self):
        v = ch9_scope.scope_gate(_ctx())
        self.assertEqual(v.evidence_extra["action"], "passive_discovery")

    def test_ac16_opsec_three_advice(self):
        v = ch9_scope.opsec_advice(_ctx())
        self.assertEqual(len(v.evidence_extra["advice"]), 3)


class GpuTests(unittest.TestCase):
    def test_ac17_affected_version_exploitable(self):
        v = ch9_gpu.gpu_escape_verdict(_ctx(
            gpu_toolkit_version="1.17.7-1", gpu_hook_surface=True,
            gpu_env_injection=True))
        self.assertIs(v.outcome, EXPLOITED)
        self.assertEqual(v.evidence_extra["cve"], "CVE-2025-23266")

    def test_ac17_no_toolkit_blocked(self):
        v = ch9_gpu.gpu_escape_verdict(_ctx())
        self.assertIs(v.outcome, BLOCKED)
        self.assertEqual(v.reason, "no_tool")

    def test_ac17_safe_version_absent(self):
        v = ch9_gpu.gpu_escape_verdict(_ctx(gpu_toolkit_version="1.17.8"))
        self.assertIs(v.outcome, ABSENT)
        self.assertEqual(v.reason, "none_found")


class RunnerTests(unittest.TestCase):
    def test_ac18_all_verdicts_have_command_output(self):
        ctx = _ctx(gpu_toolkit_version="1.17.7", k8s_api_host="h", k8s_api_port="6443")
        verdicts = ch9_runner.run_ch9(ctx)
        self.assertGreaterEqual(len(verdicts), 10)
        for v in verdicts:
            self.assertTrue(v.command, v.step_id)
            self.assertTrue(v.output, v.step_id)

    def test_ac20_unknown_step_raises(self):
        with self.assertRaises(ValueError):
            ch9_runner.run_ch9(_ctx(ch9_step_ids=("ch9-unknown",)))

    def test_ac18_evidence_contract_three_pieces(self):
        """AC-18：每步经证据 seam 落盘，记录含命令/输出/截图钩子。"""
        fake = FakeEvidence()
        ctx = _ctx(evidence=fake, gpu_toolkit_version="1.17.7",
                   k8s_api_host="h", k8s_api_port="6443",
                   ch9_step_ids=("ch9-gpu", "ch9-opsec"))
        verdicts = ch9_runner.run_ch9(ctx)
        self.assertEqual(len(fake.records), len(verdicts))
        for record in fake.records:
            with self.subTest(step=record["step_id"]):
                self.assertTrue(record["command"].strip())
                self.assertTrue(record["output"].strip())
                self.assertTrue(record.get("shot_cmd") or record.get("screenshot"))

    def test_ac18_strict_fail_marks_evidence_ok_false(self):
        """AC-18：证据 seam 失败（strict 非零）须标记 evidence_ok=False。"""
        fake = FakeEvidence(exit_code=1, error="missing screenshot")
        ctx = _ctx(evidence=fake, ch9_step_ids=("ch9-opsec",))
        verdicts = ch9_runner.run_ch9(ctx)
        self.assertFalse(verdicts[0].evidence_ok)
        self.assertIn("evidence_error", verdicts[0].evidence_extra)


if __name__ == "__main__":
    unittest.main()
