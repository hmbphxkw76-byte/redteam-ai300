#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""threat-model 单元测试（S2）：AC1–AC8 验收条件 + 外部行为契约。

仅测外部行为（输入→ThreatModel→markdown 四节/质量门/字段），不断言实现细节。
纯函数 + 注入时钟，无网络、无 LLM、无攻击框架（矩阵 ⑬）。
"""
import io
import json
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stdout

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from tools.threat_model import (  # noqa: E402
    build_threat_model,
    render,
    high_value_only,
    score_and_rank,
    DECOY,
    ThreatModel,
)
from tools.threat_model.decoy import judge_decoy  # noqa: E402
from tools.threat_model.classify import enrich  # noqa: E402


# —— 共享 fixture：recon 七字段清单 + 分析师分类层 ——
INVENTORY = {
    "target": "192.168.40.189",
    "profile": "passive",
    "assets": [
        {"asset_id": "ai-llm-a-01", "category": "LLM引擎", "product": "vLLM",
         "version": "0.6.1", "endpoint": "http://t:8000",
         "credential_hint": "Bearer-1a2b3c4d", "evidence_step": "loot/recon-01.md"},
        {"asset_id": "ai-rag-b-01", "category": "RAG库", "product": "LangChain",
         "version": "0.3.0", "endpoint": "http://t:8080",
         "credential_hint": "", "evidence_step": "loot/recon-03.md"},
        {"asset_id": "vec-c-01", "category": "向量库", "product": "Milvus",
         "version": "2.4", "endpoint": "http://t:19530",
         "credential_hint": "", "evidence_step": "loot/recon-04.md"},
        {"asset_id": "trad-d-01", "category": "传统向量机", "product": "Apache",
         "version": "2.4", "endpoint": "http://t:80",
         "credential_hint": "", "evidence_step": "loot/recon-07.md"},
        {"asset_id": "dc-e-01", "category": "域控", "product": "AD DS",
         "version": "2019", "endpoint": "ldap://t:389",
         "credential_hint": "", "evidence_step": "loot/recon-07.md"},
        {"asset_id": "decoy-f-01", "category": "诱饵机", "product": "nginx",
         "version": "1.27.5", "endpoint": "http://t:8081",
         "credential_hint": "", "evidence_step": "loot/recon-07.md"},
    ],
}

CLASSIFICATION = {
    "ai-llm-a-01": {"score_class": "AI向量机", "attack_surface": "D3",
                    "trust_zone": "内网", "reachable": True,
                    "depends_on": ["trad-d-01"]},
    "ai-rag-b-01": {"score_class": "独立机", "attack_surface": "D5",
                    "trust_zone": "独立可达", "reachable": True},
    "vec-c-01": {"score_class": "AI向量机", "attack_surface": "D6",
                 "trust_zone": "内网", "reachable": True,
                 "depends_on": ["trad-d-01"]},
    "trad-d-01": {"score_class": "传统向量机", "attack_surface": "D1",
                  "trust_zone": "公网入口", "reachable": True},
    "dc-e-01": {"score_class": "域控", "attack_surface": "D1",
                "trust_zone": "内网", "reachable": True},
    "decoy-f-01": {"score_class": "诱饵机", "decoy": True,
                   "decoy_dims": {"behavior": True, "vuln_absent": True,
                                  "no_value": True},
                   "decoy_elapsed_minutes": 12,
                   "decoy_reason": "无 AI 面、无高价值服务"},
}


def _tm():
    return build_threat_model(INVENTORY, CLASSIFICATION)


class ScoreTests(unittest.TestCase):
    """AC1 排序：分值降序 + 攻击面归属 D1–D11。"""

    def test_score_rank_desc(self):
        tm = _tm()
        ids = [a.asset_id for a in tm.high_value]
        scores = [a.score for a in tm.high_value]
        self.assertEqual(scores, sorted(scores, reverse=True))
        # AI向量机=独立机(15) 位列前三，传统(10) 次之，域控(5)，诱饵(0) 置底
        self.assertEqual(ids[-1], "decoy-f-01")
        self.assertEqual(tm.high_value[0].score, 15)
        self.assertIn("trad-d-01", ids[:4])

    def test_ai_vector_and_standalone_tie_at_top(self):
        tm = _tm()
        top = [a.score_class for a in tm.high_value[:3]]
        self.assertEqual(top, ["AI向量机", "独立机", "AI向量机"])

    def test_attack_surface_in_domains(self):
        tm = _tm()
        for a in tm.high_value:
            if a.attack_surface:
                self.assertIn(a.attack_surface, {"D%d" % i for i in range(1, 12)})

    def test_unknown_score_class_defaults_zero(self):
        inv = {"target": "t", "assets": [
            {"asset_id": "x-1", "category": "LLM引擎", "product": "p",
             "endpoint": "e", "credential_hint": "", "evidence_step": "s"}]}
        tm = build_threat_model(inv, {"x-1": {"score_class": "不存在的分类"}})
        self.assertEqual(tm.high_value[0].score_class, "不可判定")
        self.assertEqual(tm.high_value[0].score, 0)

    def test_high_value_only_excludes_decoys(self):
        views = enrich(INVENTORY, CLASSIFICATION)
        hv = high_value_only(views)
        self.assertNotIn("decoy-f-01", [a.asset_id for a in hv])
        self.assertIn("ai-llm-a-01", [a.asset_id for a in hv])


class BoundaryPathTests(unittest.TestCase):
    """AC2 信任边界 + 最短路径字段齐全。"""

    def test_trust_boundaries_grouped(self):
        tm = _tm()
        self.assertIn("内网", tm.boundaries)
        self.assertIn("独立可达", tm.boundaries)
        self.assertIn("公网入口", tm.boundaries)
        self.assertIn("ai-llm-a-01", tm.boundaries["内网"])

    def test_path_fields_complete(self):
        tm = _tm()
        self.assertTrue(tm.paths)
        for p in tm.paths:
            self.assertTrue(p.target_asset)
            self.assertTrue(p.stages)
            self.assertIsInstance(p.est_minutes, int)
            self.assertIsInstance(p.depends_on, list)
            self.assertIn(p.status, ("可达", "待补"))

    def test_missing_dependency_marks_待补(self):
        cls = dict(CLASSIFICATION)
        cls["ai-llm-a-01"] = dict(cls["ai-llm-a-01"],
                                  depends_on=["nonexistent-gw"])
        tm = build_threat_model(INVENTORY, cls)
        path = next(p for p in tm.paths if p.target_asset == "ai-llm-a-01")
        self.assertEqual(path.status, "待补")

    def test_ai_vector_subskill_coverage(self):
        # SKILL 第 13/28 行：AI 向量机路径须拉动 D6(embeddings)/D9(infra) 等链式子技能
        tm = _tm()
        path = next(p for p in tm.paths if p.target_asset == "ai-llm-a-01")
        for sk in ("attack-ai-agent", "attack-multi-agent", "attack-rag",
                   "attack-embeddings", "attack-mcp-tool", "attack-infra"):
            self.assertIn(sk, path.depends_on)


class DecoyTests(unittest.TestCase):
    """AC3 诱饵时间盒：三维度 + ≤30min 硬约束。"""

    def test_decoy_verdict_in_timebox(self):
        tm = _tm()
        self.assertEqual(len(tm.decoys), 1)
        d = tm.decoys[0]
        self.assertEqual(d.verdict, "诱饵机")
        self.assertTrue(d.abandoned)
        self.assertLessEqual(d.elapsed_minutes, 30)

    def test_timebox_exceeded_forces_abandon(self):
        tm = _tm()
        a = next(x for x in tm.high_value if x.asset_id == "decoy-f-01")
        d = judge_decoy(a, dims={"behavior": True, "vuln_absent": True,
                                 "no_value": True}, elapsed_minutes=31)
        self.assertEqual(d.verdict, "判定不确定")
        self.assertTrue(d.abandoned)
        self.assertIn("放弃", d.reason)
        self.assertTrue(d.timestamp)


class GraphTests(unittest.TestCase):
    """AC4 攻击图：根=最高杠杆、诱饵排除、§4.5 编排顺序。"""

    def test_decoys_excluded_from_graph(self):
        tm = _tm()
        self.assertNotIn("decoy-f-01", tm.graph["nodes"])
        self.assertIn("decoy-f-01", tm.graph["excluded_decoys"])

    def test_roots_are_high_leverage(self):
        tm = _tm()
        for r in tm.graph["roots"]:
            self.assertIn(r, ("ai-llm-a-01", "ai-rag-b-01", "vec-c-01"))

    def test_order_puts_ai_first_dc_last(self):
        tm = _tm()
        self.assertTrue(tm.order[0].startswith(("ai-", "vec-")))
        self.assertEqual(tm.order[-1], "dc-e-01")
        self.assertNotIn("decoy-f-01", tm.order)


class ReuseEvidenceTests(unittest.TestCase):
    """AC5/AC6/AC7：下游复用锚点 + 来源锚点 + 无明文凭据。"""

    def test_markdown_has_asset_id_anchor(self):
        md = render(_tm())
        self.assertIn("`ai-llm-a-01`", md)
        self.assertIn("loot/recon-01.md", md)

    def test_markdown_has_four_sections(self):
        md = render(_tm())
        for sec in ("资产计分排序", "信任边界与最短攻击路径",
                    "诱饵判定清单", "优先级攻击图", "质量门"):
            self.assertIn(sec, md)

    def test_reproducibility_source_anchors(self):
        # AC6：排序/路径附来源锚点（§2.2/§2.3 + 分类依据 + 时间盒时间戳）
        md = render(_tm())
        self.assertIn("§2.2/§2.3", md)          # 计分来源锚点
        self.assertIn("分类依据", md)            # 分类依据锚点
        self.assertIn("score_class", md)         # 分类来源字段
        self.assertIn("路径依据", md)            # 路径推导依据

    def test_no_plaintext_secret(self):
        md = render(_tm())
        # 凭据仅以 credential_hint 指纹形态出现，不含明文值（无 8 位裸哈希散落）
        self.assertIn("Bearer-1a2b3c4d", md)  # 指纹线索被保留（可下游复用）
        # 去除已知指纹后，不得再出现任何 Bearer- 明文 token
        stripped = md.replace("Bearer-1a2b3c4d", "")
        self.assertNotIn("Bearer-", stripped)


class FrameworkTests(unittest.TestCase):
    """AC8 框架：实现不 import 攻击框架（矩阵 ⑬）。"""

    def test_no_attack_framework_imports(self):
        pkg = os.path.join(ROOT, "tools", "threat_model")
        for fn in os.listdir(pkg):
            if not fn.endswith(".py"):
                continue
            with open(os.path.join(pkg, fn), encoding="utf-8") as f:
                src = f.read()
            for banned in ("import pyrit", "import garak", "import promptfoo",
                           "pyrit.orchestrator", "Orchestrator",
                           "AzureOpenAIChatTarget"):
                self.assertNotIn(banned, src, "%s 含禁用对象 %s" % (fn, banned))


class QualityGateTests(unittest.TestCase):
    """质量门：四项齐全判定。"""

    def test_full_model_passes_quality_gate(self):
        tm = _tm()
        self.assertEqual(tm.quality_gate(), [])

    def test_empty_model_fails_quality_gate(self):
        empty = ThreatModel(target="t", high_value=[], boundaries={},
                            paths=[], decoys=[], graph={}, order=[])
        missing = empty.quality_gate()
        self.assertIn("高价值资产清单", missing)
        self.assertIn("优先级攻击图", missing)


class CliTests(unittest.TestCase):
    """CLI 契约：退出码、读错误、写文件、质量门失败。"""

    def _write(self, tmp, name, obj):
        path = os.path.join(tmp, name)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(obj, f, ensure_ascii=False)
        return path

    def test_cli_success_to_stdout(self):
        import json as _json
        from tools.threat_model import cli
        with tempfile.TemporaryDirectory() as tmp:
            inv = self._write(tmp, "inv.json", INVENTORY)
            cls = self._write(tmp, "cls.json", CLASSIFICATION)
            with redirect_stdout(io.StringIO()) as buf:
                rc = cli.main(["--inventory", inv, "--classification", cls])
            self.assertEqual(rc, 0)
            self.assertIn("# 威胁模型", buf.getvalue())

    def test_cli_success_to_file(self):
        from tools.threat_model import cli
        with tempfile.TemporaryDirectory() as tmp:
            inv = self._write(tmp, "inv.json", INVENTORY)
            cls = self._write(tmp, "cls.json", CLASSIFICATION)
            out = os.path.join(tmp, "model.md")
            rc = cli.main(["--inventory", inv, "--classification", cls,
                           "--out", out])
            self.assertEqual(rc, 0)
            self.assertTrue(os.path.isfile(out))

    def test_cli_missing_input_exits_1(self):
        from tools.threat_model import cli
        self.assertEqual(cli.main(["--inventory", "/nope.json",
                                   "--classification", "/nope2.json"]), 1)

    def test_cli_quality_gate_failure_exits_1(self):
        from tools.threat_model import cli
        with tempfile.TemporaryDirectory() as tmp:
            # 空资产清单 → 质量门缺失 → 退出码 1
            empty_inv = {"target": "t", "assets": []}
            inv = self._write(tmp, "inv.json", empty_inv)
            cls = self._write(tmp, "cls.json", {})
            rc = cli.main(["--inventory", inv, "--classification", cls])
            self.assertEqual(rc, 1)


if __name__ == "__main__":
    unittest.main()
