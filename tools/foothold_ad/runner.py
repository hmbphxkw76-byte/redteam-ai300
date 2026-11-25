#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""八步编排：从工件目录折叠结论，不联网、不执行 AD 工具。

输入质量分三级处置（`docs/operations/foothold-ad-design.md` §10）：
- 工件缺失或损坏 → 依赖该工件的步骤 `BLOCKED`（无可用输入，不出结论）；
- `schema_version` 不受支持 → 同步骤 `UNDETERMINED`（有输入但无法按当前判据映射）；
- 已解析但字段缺失 → 判据层 `UNDETERMINED` 并在注记写明缺哪项。
"""
import hashlib
import json
import os
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

from . import artifact, provenance
from .analyze import assess
from .evidence import STEP_COMMANDS
from .model import BLOCKED, STEP_IDS, STEP_TITLES, StepResult, UNDETERMINED

# 步骤 → 必需工件（缺一即该步 BLOCKED）。
REQUIRED_ARTIFACTS = {
    "ad-01": (artifact.TRUSTS_FILE, artifact.DIRECTORY_FILE),
    "ad-02": (artifact.DIRECTORY_FILE,),
    "ad-03": (),
    "ad-04": (artifact.TEMPLATES_FILE,),
    "ad-05": (artifact.DIRECTORY_FILE,),
    "ad-06": (artifact.TRUSTS_FILE, artifact.DIRECTORY_FILE),
    "ad-07": (),
    "ad-08": (),
}

OPTIONAL_ARTIFACTS = ("tickets.json", "proof.json")


@dataclass
class RunReport:
    """一次编排的完整结论。"""

    artifacts_dir: str
    results: Dict[str, StepResult] = field(default_factory=dict)
    loaded: Tuple[str, ...] = ()
    missing: Tuple[str, ...] = ()
    schema_errors: Mapping[str, str] = field(default_factory=dict)
    parse_errors: Mapping[str, str] = field(default_factory=dict)
    provenance_ok: bool = False
    untrusted: Tuple[str, ...] = ()

    @property
    def blocked_steps(self) -> Tuple[str, ...]:
        return tuple(s for s, r in self.results.items() if r.verdict == BLOCKED)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "artifacts_dir": self.artifacts_dir,
            "loaded": list(self.loaded),
            "missing": list(self.missing),
            "schema_errors": dict(self.schema_errors),
            "parse_errors": dict(self.parse_errors),
            "provenance": {"ok": self.provenance_ok, "untrusted": list(self.untrusted)},
            "blocked_steps": list(self.blocked_steps),
            "steps": [self.results[s].to_dict() for s in STEP_IDS if s in self.results],
        }

    def digest(self) -> str:
        """结论摘要哈希：同输入必得同值，供快照与追溯使用。"""
        payload = json.dumps(self.to_dict(), ensure_ascii=False, sort_keys=True)
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def plan_steps(steps: Optional[Iterable[str]] = None) -> Tuple[str, ...]:
    """校验并排序步骤子集；未知步骤抛 `ValueError`。"""
    if not steps:
        return STEP_IDS
    wanted = [s.strip() for s in steps if s and s.strip()]
    if not wanted:
        return STEP_IDS
    unknown = [s for s in wanted if s not in STEP_IDS]
    if unknown:
        raise ValueError("未知步骤: %s" % ", ".join(unknown))
    return tuple(s for s in STEP_IDS if s in wanted)


def _load(artifacts_dir: str, name: str) -> Tuple[Any, Optional[str], Optional[str]]:
    """返回 (payload, parse_error, schema_error)；文件不存在时 payload 为 None。"""
    path = os.path.join(artifacts_dir, name)
    if not os.path.isfile(path):
        return None, None, None
    try:
        payload = artifact.load_json(path)
    except artifact.ArtifactError as exc:
        return None, str(exc), None
    try:
        artifact.check_schema(payload, name)
    except artifact.UnsupportedSchema as exc:
        return None, None, str(exc)
    return payload, None, None


def run(artifacts_dir: str, steps: Optional[Iterable[str]] = None,
        owned: Sequence[str] = ()) -> RunReport:
    """读取 `artifacts_dir` 下工件并输出所选步骤的结论。"""
    selected = plan_steps(steps)
    report = RunReport(artifacts_dir=artifacts_dir)

    payloads: Dict[str, Any] = {}
    loaded: List[str] = []
    missing: List[str] = []
    schema_errors: Dict[str, str] = {}
    parse_errors: Dict[str, str] = {}

    for name in (artifact.DIRECTORY_FILE, artifact.TEMPLATES_FILE, artifact.TRUSTS_FILE):
        payload, parse_error, schema_error = _load(artifacts_dir, name)
        if parse_error:
            parse_errors[name] = parse_error
            missing.append(name)
            continue
        if schema_error:
            schema_errors[name] = schema_error
            continue
        if payload is None:
            missing.append(name)
            continue
        payloads[name] = payload
        loaded.append(name)

    report.loaded = tuple(loaded)
    report.missing = tuple(missing)
    report.schema_errors = schema_errors
    report.parse_errors = parse_errors

    directory = artifact.parse_directory(payloads[artifact.DIRECTORY_FILE]) \
        if artifact.DIRECTORY_FILE in payloads else None
    templates = artifact.parse_templates(payloads[artifact.TEMPLATES_FILE]) \
        if artifact.TEMPLATES_FILE in payloads else ()
    trusts = artifact.parse_trusts(payloads[artifact.TRUSTS_FILE]) \
        if artifact.TRUSTS_FILE in payloads else ()

    tickets_payload, _, _ = _load(artifacts_dir, "tickets.json")
    proof_payload, _, _ = _load(artifacts_dir, "proof.json")
    tickets = tickets_payload if isinstance(tickets_payload, list) else None
    proof = proof_payload if isinstance(proof_payload, Mapping) else None

    results = assess(directory=directory, templates=templates, trusts=trusts,
                     owned=owned, tickets=tickets, proof=proof)
    results = {step: results[step] for step in selected}

    for step, result in list(results.items()):
        schema_bad = [name for name in REQUIRED_ARTIFACTS[step] if name in schema_errors]
        absent = [name for name in REQUIRED_ARTIFACTS[step] if name in missing]
        if schema_bad and result.verdict != BLOCKED:
            results[step] = StepResult(
                step, UNDETERMINED, findings=result.findings,
                notes=tuple(schema_errors[name] for name in schema_bad))
        elif absent and result.verdict != BLOCKED:
            results[step] = StepResult(
                step, BLOCKED, findings=result.findings,
                notes=("缺少工件: %s" % ", ".join(absent),) + result.notes)
        elif not results[step].notes and results[step].verdict == UNDETERMINED:
            results[step] = StepResult(step, UNDETERMINED, notes=("工件不足以判定",))
        results[step].command = results[step].command or STEP_COMMANDS[step]

    report.results = results

    present = tuple(name for name in
                    (artifact.DIRECTORY_FILE, artifact.TEMPLATES_FILE, artifact.TRUSTS_FILE)
                    + OPTIONAL_ARTIFACTS
                    if os.path.isfile(os.path.join(artifacts_dir, name)))
    if present:
        verified = provenance.verify(artifacts_dir, files=present)
        report.provenance_ok = verified.ok
        report.untrusted = verified.untrusted
    return report
