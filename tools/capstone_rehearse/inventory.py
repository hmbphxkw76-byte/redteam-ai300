#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""S-1 seam：阶段就绪来源（设计 §4）。

默认 adapter 扫仓库，按 `GOVERNANCE.md#L141-L151` 的九阶段流水线与
`docs/research/capstone-rehearse-canonical.md` §3 对象映射给出四项就绪判据；
测试用 adapter 注入内存清单，使走查可确定性复现（AC-02 删除法）。
"""
from __future__ import annotations

import glob
import os
from typing import Dict, Iterable, Optional, Tuple

from .model import Stage, StageEvidence

# (stage_id, 名称, 代表技能, 阶段, 技能集合, 实现落点, 证据契约测试, 演练片段目录)
STAGE_SPECS = (
    ("cr-01", "威胁建模", "threat-model", "前置",
     ("threat-model",), ("tools/threat_model",),
     ("tests/test_threat_model.py",), ("evidence/threat-model-drill",)),
    ("cr-02", "侦察枚举", "recon-ai", "前置",
     ("recon-ai",), ("tools/recon_ai",),
     ("tests/test_recon_ai.py", "tests/test_recon_evidence_contract.py"),
     ("evidence/recon-ai-drill",)),
    ("cr-03", "立足点", "foothold-traditional", "前置",
     ("foothold-traditional",), ("tools/foothold_traditional",),
     ("tests/test_foothold_traditional_evidence_contract.py",),
     ("evidence/foothold-traditional-drill",)),
    ("cr-04", "链式横向 + AI 向量利用", "attack-ai-agent", "利用",
     ("attack-ai-agent", "attack-rag", "attack-mcp-tool", "attack-embeddings",
      "attack-multi-agent", "attack-supply-chain", "attack-infra"),
     ("tools/attack_ai_agent", "tools/attack_rag", "tools/attack_mcp_tool",
      "tools/attack_embeddings", "tools/attack_multi_agent",
      "tools/attack_supply_chain", "tools/attack_infra"),
     ("tests/test_attack_rag_evidence_contract.py",
      "tests/test_attack_mcp_tool_evidence_contract.py",
      "tests/test_attack_multi_agent_evidence_contract.py"),
     ("evidence/attack-ai-agent-drill", "evidence/attack-rag-drill")),
    ("cr-05", "独立机", "attack-mcp-tool", "利用",
     ("attack-mcp-tool", "attack-infra"), ("tools/attack_mcp_tool", "tools/attack_infra"),
     ("tests/test_attack_mcp_tool_evidence_contract.py",
      "tests/test_attack_infra_evidence_contract.py"),
     ("evidence/attack-mcp-tool-drill",)),
    ("cr-06", "战利品沉淀", "loot-manage", "收敛",
     ("loot-manage",), ("tools/loot_manage",),
     ("tests/test_loot_manage.py", "tests/test_loot_manage_evidence_contract.py"),
     ("evidence/loot-manage-drill",)),
    ("cr-07", "域控收敛", "domain-controller", "收敛",
     ("verify-evidence",), ("tools/verify_evidence.py",),
     ("tests/test_verify_evidence.py",),
     ("evidence/verify-evidence-drill",)),
    ("cr-08", "证据校验", "verify-evidence", "收敛",
     ("verify-evidence",), ("tools/verify_evidence.py",),
     ("tests/test_verify_evidence.py",),
     ("evidence/verify-evidence-drill",)),
    ("cr-09", "报告生成", "report-exam", "收敛",
     ("report-exam",), ("report_exam",),
     ("tests/test_report_exam.py", "tests/test_report_exam_evidence_contract.py"),
     ("evidence/report-exam-drill",)),
)


def stages_from_specs() -> Tuple[Stage, ...]:
    return tuple(Stage(s[0], s[1], s[2], s[3]) for s in STAGE_SPECS)


def spec_for(stage_id: str):
    for spec in STAGE_SPECS:
        if spec[0] == stage_id:
            return spec
    raise KeyError("未知阶段：%s" % stage_id)


class StageInventory:
    """S-1 seam 接口：stages() 与 evidence_for()。"""

    def stages(self) -> Tuple[Stage, ...]:
        raise NotImplementedError

    def evidence_for(self, stage_id: str) -> StageEvidence:
        raise NotImplementedError


class RepoStageInventory(StageInventory):
    """生产 adapter：扫仓库路径，不解析片段正文、不调子进程。"""

    def __init__(self, root: str = "."):
        self.root = root

    def _exists(self, rel: str) -> bool:
        return os.path.exists(os.path.join(self.root, rel))

    def stages(self) -> Tuple[Stage, ...]:
        return stages_from_specs()

    def evidence_for(self, stage_id: str) -> StageEvidence:
        spec = spec_for(stage_id)
        skills, impls, tests, fragment_dirs = spec[4], spec[5], spec[6], spec[7]
        return StageEvidence(
            skill_body=all(self._exists("skills/%s/SKILL.md" % s) for s in skills),
            implementation=any(self._exists(p) or self._exists(p + ".py") for p in impls),
            evidence_contract=any(self._exists(p) for p in tests),
            fragment_path=any(
                glob.glob(os.path.join(self.root, d, "*.md")) for d in fragment_dirs),
        )


class MemoryStageInventory(StageInventory):
    """测试 adapter：注入阶段清单与逐项删除的就绪四要素。"""

    def __init__(self, stages: Optional[Iterable[Stage]] = None,
                 evidence: Optional[Dict[str, StageEvidence]] = None):
        self._stages = tuple(stages) if stages is not None else stages_from_specs()
        self._evidence = dict(evidence or {})

    def stages(self) -> Tuple[Stage, ...]:
        return self._stages

    def evidence_for(self, stage_id: str) -> StageEvidence:
        return self._evidence.get(stage_id, StageEvidence(True, True, True, True))
