"""agent.log 解析纯函数测试（Ch11 rag-10 · AC-2/3/4/5）。"""
import unittest

from tools.attack_rag.agent_log import (classify_events, has_periodic_heartbeat,
                                        infer_agent_identity, infer_trigger_keyword,
                                        key_path_candidates, extract_pem,
                                        check_quiz_format)


class AgentLogTests(unittest.TestCase):
    def test_ac2_classify_four_events_and_lm_error_separate(self):
        events = [
            {"event": "ingest_ok", "path": "01.md"},
            {"event": "lm_response", "query": "hi"},
            {"event": "lm_error", "msg": "down"},
            {"event": "heartbeat", "ts": "2025-10-09T15:27:06"},
            {"event": "heartbeat", "ts": "2025-10-09T15:28:06"},
        ]
        kinds = classify_events(events)
        self.assertEqual(len(kinds["ingest_ok"]), 1)
        self.assertEqual(len(kinds["lm_response"]), 1)
        self.assertEqual(len(kinds["lm_error"]), 1)   # 单列，不混入 lm_response
        self.assertEqual(len(kinds["heartbeat"]), 2)
        self.assertTrue(has_periodic_heartbeat(kinds["heartbeat"], 60))

    def test_ac3_trigger_keyword_repeat(self):
        word = "oiajwdoiajwoidajoiwdjaoiwdja"
        responses = [{"query": "normal question"},
                     {"query": word}, {"query": word}, {"query": word}]
        self.assertEqual(infer_trigger_keyword(responses), word)
        self.assertIsNone(infer_trigger_keyword([{"query": "normal question"}]))

    def test_ac4_identity_fullcontrol_and_hr_filter(self):
        rows = [{"identity": "NT AUTHORITY\\SYSTEM", "rights": "FullControl"},
                {"identity": "MEGACORPONE\\lily.fisher", "rights": "FullControl"},
                {"identity": "BUILTIN\\Users", "rights": "Read"}]
        res = infer_agent_identity(rows, hr_members=("MEGACORPONE\\lily.fisher",))
        self.assertEqual(res["identity"], "MEGACORPONE\\lily.fisher")
        self.assertFalse(res["ambiguous"])
        # 多 FullControl 且 HR 无法消歧 → 歧义标记
        rows2 = [{"identity": "A", "rights": "FullControl"},
                 {"identity": "B", "rights": "FullControl"}]
        self.assertTrue(infer_agent_identity(rows2, hr_members=())["ambiguous"])

    def test_ac5_key_path_order_and_pem(self):
        paths = key_path_candidates("lily.fisher")
        self.assertIn("id_ed25519", paths[0])
        self.assertIn("id_rsa", paths[1])
        self.assertIn("id_ecdsa", paths[2])
        text = "head\n-----BEGIN OPENSSH PRIVATE KEY-----\nABC\nDEF\n-----END OPENSSH PRIVATE KEY-----\ntail"
        pem = extract_pem(text)
        self.assertIn("-----BEGIN OPENSSH PRIVATE KEY-----", pem)
        self.assertIn("\nABC\nDEF\n", pem)
        self.assertEqual(extract_pem("no key here"), "")

    def test_quiz_format(self):
        self.assertTrue(check_quiz_format("10.0.17763.1234", "os_build"))
        self.assertFalse(check_quiz_format("not-a-build", "os_build"))
        self.assertTrue(check_quiz_format("10.13.37.8:8080", "llm_addr"))
        self.assertFalse(check_quiz_format("10.13.37.8", "llm_addr"))


if __name__ == "__main__":
    unittest.main()
