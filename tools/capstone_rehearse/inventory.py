#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""S-1 seam：阶段就绪来源（设计 §4）。

默认 adapter 扫仓库，按 `GOVERNANCE.md#L141-L151` 的九阶段流水线与
`docs/research/capstone-rehearse-canonical.md` §3 对象映射给出四项就绪判据；
测试用 adapter 注入内存清单，使走查可确定性复现（AC-02 删除法）。
"""
from __future__ import annotations

import glob
import json
import os
from typing import Dict, Iterable, Optional, Tuple

from .model import Stage, StageEvidence

# 单一事实源（C1）：阶段→技能/实现/证据契约测试/片段目录的登记只存在于
# stage_manifest.json。tools/ 与 tests/ 目录重组时只改该清单，不改本模块。
MANIFEST_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                             "stage_manifest.json")


def _load_stage_specs(path: str = MANIFEST_PATH):
    """从 JSON 清单构建 STAGE_SPECS；保持既有 8 元组形态，下游接口不变。"""
    with open(path, encoding="utf-8") as handle:
        payload = json.load(handle)
    return tuple(
        (row["stage_id"], row["name"], row["skill"], row["phase"],
         tuple(row["skills"]), tuple(row["implementation"]),
         tuple(row["evidence_contract"]), tuple(row["fragment_dirs"]))
        for row in payload["stages"]
    )


# (stage_id, 名称, 代表技能, 阶段, 技能集合, 实现落点, 证据契约测试, 演练片段目录)
STAGE_SPECS = _load_stage_specs()


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
