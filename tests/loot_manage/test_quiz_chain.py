"""quiz_answer 与凭据串链测试（Ch11 模板 6 · AC-1/2/3/4）。"""
import unittest

from tools.loot_manage.registry import (parse_registry, check_quiz_format,
                                        QUIZ_HEADING)

REG = """| 编号 | 类型 | 内容 | 来源主机 | 证据片段路径 | 时间戳 | 状态 | 双通道 |
|---|---|---|---|---|---|---|---|
| L-01 | 凭据 | ED25519 key | CLIENT04 | loot/sc.md | 2025-10-09 | 有效 | 面板=x;截图=y |

## 攻击路径
- lily.fisher ED25519 key=ED25519 fp=SHA256:abc123 → CLIENT04 SYSTEM

## 问答取证
- OS build 号 | 10.0.17763.1234 | os_build | loot/quiz.md
- LLM 推理地址 | 10.13.37.8:8080 | llm_addr | loot/quiz.md
"""


class QuizChainTests(unittest.TestCase):
    def test_ac1_parse_quiz_without_breaking_existing(self):
        reg = parse_registry(REG)
        self.assertEqual(len(reg.rows), 1)
        self.assertEqual(len(reg.attack_paths), 1)  # 既有契约不变
        self.assertEqual(len(reg.quiz_answers), 2)
        self.assertEqual(reg.quiz_answers[0]["fmt"], "os_build")

    def test_ac2_format_regex(self):
        self.assertTrue(check_quiz_format("10.0.17763.1234", "os_build")[0])
        self.assertFalse(check_quiz_format("bad", "os_build")[0])
        self.assertTrue(check_quiz_format("10.13.37.8:8080", "llm_addr")[0])
        self.assertFalse(check_quiz_format("10.13.37.8", "llm_addr")[0])

    def test_ac3_credential_chain_reuses_attack_paths(self):
        reg = parse_registry(REG)
        chain = reg.credential_chain()
        self.assertEqual(len(chain), 1)
        self.assertEqual(chain[0]["key_type"], "ED25519")
        self.assertEqual(chain[0]["fingerprint"], "SHA256:abc123")
        self.assertTrue(chain[0]["optional"])  # 指纹缺省不阻断

    def test_ac4_vrf09_in_checks(self):
        from tools import verify_evidence as VE
        self.assertIn("vrf-09", VE.CHECKS)
        bad = VE.check_vrf09({"quiz_answers": [{"q": "OS", "a": "bad", "fmt": "os_build"}]})
        self.assertFalse(bad["ok"])
        empty = VE.check_vrf09({"quiz_answers": []})
        self.assertTrue(empty["ok"])  # 未登记不阻断


if __name__ == "__main__":
    unittest.main()
