#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""AD 域渗透判据类型（唯一事实源）。

判据取值域沿用仓库既有五值（`EXPLOITED` / `EXPOSED_NO_AUTH` / `AUTH_REQUIRED` /
`ABSENT` / `BLOCKED`）并追加 `UNDETERMINED` 表达「工件字段缺失、证据不足」，
不新造第六种语义（C1：五值本体见 `tools/attack_infra/model.py`，此处不复述）。
"""
from dataclasses import dataclass, field
from typing import Any, Dict, Tuple

EXPLOITED = "EXPLOITED"
EXPOSED_NO_AUTH = "EXPOSED_NO_AUTH"
AUTH_REQUIRED = "AUTH_REQUIRED"
ABSENT = "ABSENT"
BLOCKED = "BLOCKED"
UNDETERMINED = "UNDETERMINED"
VERDICTS = (EXPLOITED, EXPOSED_NO_AUTH, AUTH_REQUIRED, ABSENT, BLOCKED, UNDETERMINED)

STEP_IDS = (
    "ad-01", "ad-02", "ad-03", "ad-04",
    "ad-05", "ad-06", "ad-07", "ad-08",
)

STEP_TITLES = {
    "ad-01": "域环境测绘与信任枚举",
    "ad-02": "Kerberos 可攻击账户枚举",
    "ad-03": "票据获取（Kerberoast / AS-REP）",
    "ad-04": "ADCS 模板利用面判定",
    "ad-05": "目录复制权限（DCSync 面）",
    "ad-06": "域信任滥用路径",
    "ad-07": "域控收敛与 proof.txt 取证",
    "ad-08": "路径沉淀与移交",
}


@dataclass(frozen=True)
class Finding:
    """单条判据命中的事实；`detail` 只写依据，不写明文凭据。"""

    kind: str
    subject: str
    detail: str = ""

    def as_text(self) -> str:
        return "%s:%s" % (self.kind, self.subject) if not self.detail else (
            "%s:%s (%s)" % (self.kind, self.subject, self.detail))


@dataclass
class StepResult:
    """单步结论；字段与 `collect_evidence.py` 参数同构，便于组装证据。"""

    step_id: str
    verdict: str = UNDETERMINED
    findings: Tuple[Finding, ...] = ()
    notes: Tuple[str, ...] = ()
    command: str = ""
    evidence_path: str = ""
    evidence_ok: bool = True
    evidence_extra: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if self.step_id not in STEP_IDS:
            raise ValueError("未知步骤: %r" % (self.step_id,))
        if self.verdict not in VERDICTS:
            raise ValueError("未知判据: %r" % (self.verdict,))
        self.findings = tuple(self.findings)
        self.notes = tuple(self.notes)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "step_id": self.step_id,
            "title": STEP_TITLES[self.step_id],
            "verdict": self.verdict,
            "findings": [f.as_text() for f in self.findings],
            "notes": list(self.notes),
            "command": self.command,
            "evidence_path": self.evidence_path,
            "evidence_ok": self.evidence_ok,
        }
