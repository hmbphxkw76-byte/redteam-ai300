#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""步骤契约（稳定标识 rag-00..rag-05）。

每个标识恰好对应一次 `collect_evidence.py --step <id> --strict` 调用，
且 `skills/attack-rag/examples/evidence-demo.md` 的 rag-01/rag-02 语义与此一致
（rag-01 = 知识库投毒，rag-02 = 检索层操纵前后对照）。标识集合是证据契约
夹具的机器判据，属对外契约，不随实现重构改动；v1.1 依 SKILL.md 前置新增
`rag-00`（定位 RAG 攻击面 / 护栏基线），属**契约扩展**而非重构改动。
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class StepSpec:
    """一个攻击步骤的静态契约。"""

    step_id: str
    path: str
    title: str
    objective: str
    ai_log: bool = False     # 该步是否必须带 AI 交互日志（§6.3）


STEP_SPECS = (
    StepSpec("rag-00", "", "定位 RAG 攻击面：组件 / 下游 agent / 护栏基线",
             "复用 recon-ai 资产清单确认向量库、检索入口与摄取通道，识别下游 agent，"
             "并记录护栏基线作为投毒效果对照（SKILL.md 前置）", False),
    StepSpec("rag-01", "A", "知识库投毒：注入带指令的恶意文档",
             "经 PoisonedRAG 前置问题法把恶意文档写入知识库，确认进入目标查询 top-k", False),
    StepSpec("rag-02", "A", "检索层操纵前后对照：恶意文档进入 top-k",
             "以白盒 embedding 碰撞注入 5 篇，取证 top-k before/after 排名变化与命中率", True),
    StepSpec("rag-03", "B", "间接注入：检索片段内嵌指令触发下游",
             "把指令藏入检索片段，经 XPIATestWorkflow 触发下游 agent 代理执行", True),
    StepSpec("rag-04", "C", "下游决策影响：baseline vs manipulated",
             "同一查询仅换上下文做双次捕获，证明决策差异由检索操纵引起", True),
    StepSpec("rag-05", "", "flag 取证（双通道一致）",
             "取得立足点后定位 ai_vector.txt，面板值与截图值一致；缺席走校验预言机", False),
)

STEP_IDS = tuple(s.step_id for s in STEP_SPECS)

STEP_BY_ID = {s.step_id: s for s in STEP_SPECS}

# 前置步骤恒定最先（SKILL.md 执行体：定位 → A → B → C → flag）
SURFACE_STEP = "rag-00"
FLAG_STEP = "rag-05"

PATH_STEPS = {
    "A": ("rag-01", "rag-02"),
    "B": ("rag-03",),
    "C": ("rag-04",),
}


def steps_for_paths(paths=("A", "B", "C"), step=""):
    """按「定位 → A → B → C → flag 取证」顺序返回所选步骤。"""
    if step:
        if step not in STEP_BY_ID:
            raise ValueError("未知步骤标识：%s（允许 %s）"
                             % (step, ", ".join(STEP_IDS)))
        return (STEP_BY_ID[step],)
    unknown = [p for p in paths if p not in PATH_STEPS]
    if unknown:
        raise ValueError("未知攻击路径：%s（允许 A/B/C）" % ", ".join(unknown))
    out = [STEP_BY_ID[SURFACE_STEP]]
    for path in ("A", "B", "C"):
        if path in paths:
            out.extend(STEP_BY_ID[s] for s in PATH_STEPS[path])
    out.append(STEP_BY_ID[FLAG_STEP])
    return tuple(out)
