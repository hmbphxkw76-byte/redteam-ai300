#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Ch11 增量步骤契约与编排（rag-10 日志回读闭环）。

独立于 steps.py 冻结的 6-ID 主链（rag-00..05）与 CH5_STEP_IDS（rag-06..09）；
沿用 ch5.py 的独立步骤契约模式，共用 collect_evidence 严格模式 seam。
"""
import shlex
from typing import List, Optional, Tuple

from .agent_log import (classify_events, has_periodic_heartbeat, infer_agent_identity,
                        infer_trigger_keyword, key_path_candidates, extract_pem)
from .model import AttackReport, AttackRequest, StepVerdict, FlagProof
from .runner import Runtime, _emit, _resolve, _StepRun
from .steps import StepSpec

CH11_STEP_SPECS = (
    StepSpec("rag-10", "D", "日志回读闭环：agent.log 事件分类/触发词/ACL 身份推断/密钥路径/PEM 抽取",
             "解析 agent.log 四类事件（含 heartbeat 60s 周期），从重复无意义串推断触发词，"
             "按 ACL FullControl 推断 agent 运行身份，迭代三种密钥路径并抽取私钥块"
             "（Ch11 §11.5 L1295-1386）", True),
)
CH11_STEP_IDS: Tuple[str, ...] = tuple(s.step_id for s in CH11_STEP_SPECS)


def _ch11_command(spec: StepSpec, request: AttackRequest) -> str:
    return shlex.join(["python", "tools/attack_rag/ch11_cli.py", "--step",
                       spec.step_id, "--target", request.target])


def run_ch11(request: AttackRequest, runtime: Optional[Runtime] = None) -> AttackReport:
    """执行 rag-10 并落盘证据；返回与主链同型的 AttackReport。"""
    rt = _resolve(request, runtime)
    flag = FlagProof(request.flag_panel, request.flag_shot, request.flag_oracle)
    verdicts: List[StepVerdict] = []
    for spec in CH11_STEP_SPECS:
        if request.step and request.step != spec.step_id:
            continue
        run = _dispatch(spec.step_id, request)
        path = _emit(request, rt, spec, run, command=_ch11_command(spec, request))
        verdicts.append(StepVerdict(
            step_id=spec.step_id, path=spec.path, title=spec.title,
            level=run.level, reason=run.reason, command=_ch11_command(spec, request),
            output=run.output, evidence_path=path))
    return AttackReport(request=request, backend=rt.backend.describe(),
                        verdicts=tuple(verdicts), flag=flag,
                        object_graph={"ch11_steps": list(CH11_STEP_IDS)})


def _demo_events():
    return [
        {"event": "ingest_ok", "path": "doc-01", "doc_id": "a"},
        {"event": "lm_response", "query": "What is the expense process?"},
        {"event": "lm_response", "query": "oiajwdoiajwoidajoiwdjaoiwdja"},
        {"event": "lm_response", "query": "oiajwdoiajwoidajoiwdjaoiwdja"},
        {"event": "lm_response", "query": "oiajwdoiajwoidajoiwdjaoiwdja"},
        {"event": "lm_error", "msg": "LLM backend unavailable"},
        {"event": "heartbeat", "ts": "2025-10-09T15:27:06", "kb_dir": "KB"},
        {"event": "heartbeat", "ts": "2025-10-09T15:28:06", "kb_dir": "KB"},
        {"event": "heartbeat", "ts": "2025-10-09T15:29:06", "kb_dir": "KB"},
    ]


def _dispatch(step_id: str, request: AttackRequest) -> _StepRun:
    if step_id != "rag-10":
        raise ValueError("未知 Ch11 步骤标识：%s" % step_id)
    events = _demo_events()
    kinds = classify_events(events)
    trigger = infer_trigger_keyword(kinds["lm_response"])
    identity = infer_agent_identity(
        [{"identity": "NT AUTHORITY\\SYSTEM", "rights": "FullControl"},
         {"identity": "BUILTIN\\Administrators", "rights": "FullControl"},
         {"identity": "MEGACORPONE\\lily.fisher", "rights": "FullControl"}],
        hr_members=("MEGACORPONE\\lily.fisher", "MEGACORPONE\\ethan.palmer"))
    keys = key_path_candidates("lily.fisher")
    pem = extract_pem("noise\n-----BEGIN OPENSSH PRIVATE KEY-----\nAAA\n-----END OPENSSH PRIVATE KEY-----\ntail")
    lines = [
        "事件分类：%s" % ", ".join("%s=%d" % (k, len(v)) for k, v in kinds.items()),
        "heartbeat 60s 周期：%s（静态样例，实网须复核）" % has_periodic_heartbeat(kinds["heartbeat"]),
        "触发词：%s" % (trigger or "UNDETERMINED（无重复，不臆造）"),
        "agent 身份：%s%s" % (identity["identity"] or "UNDETERMINED",
                             "（歧义）" if identity["ambiguous"] else ""),
        "密钥路径迭代：%s" % " → ".join(keys),
        "PEM 抽取：%s" % ("含 BEGIN/END 行，保留换行（%d 字符）" % len(pem) if pem else "无私钥块"),
        "Kibana 不可达时 detect/confirm 记 UNDETERMINED（不臆断无告警）",
    ]
    return _StepRun("部分生效", "日志解析离线样例完成；实网 agent.log 内容须回填，不伪造观测",
                    "\n".join(lines),
                    ai_log=("prompt: 解析 agent.log 四类事件并推断触发词\n模型: %s\n"
                            "输出: 见关键输出\n采纳: 触发词关联文件读取指令" % request.target))
