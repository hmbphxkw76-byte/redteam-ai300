"""派生式交接索引与六段一致性校验（候选 A）。

以 step_id 为唯一关联键，从既有产物派生索引；不新增权威存储、不修改
任何既有 skill/tool 语义。判定复用 GateResult（PASS/BLOCKED）。
"""
from __future__ import annotations

import re
from typing import Iterable

from .models import GateResult, Verdict

ASSET_FIELDS = (
    "asset_id", "category", "product", "version", "endpoint",
    "credential_hint", "evidence_step",
)


def derive_panel_flags(registry_text: str, with_problems: bool = False):
    """从登记簿双通道单元格派生 panel_flags，只取「面板=」列。

    截图路径是另一通道，不作为 flag 值，避免自比。
    """
    flags: dict[str, str] = {}
    problems: list[str] = []
    for line in (registry_text or "").splitlines():
        if not line.strip().startswith("|"):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) < 8:
            problems.append("登记行字段不足 8 列：%s" % line[:60])
            continue
        host = cells[3]
        dual = cells[7]
        match = re.search(r"面板=([^；;]+)", dual)
        if not match:
            continue
        panel = match.group(1).strip()
        if panel and host:
            flags[host] = panel
    return (flags, problems) if with_problems else flags


def recon_fragments_for_report(fragments: Iterable[dict], hosts: Iterable[str],
                               real_only: bool = False) -> list[dict]:
    """按 host 显式映射侦察片段；不因 synthetic 来源过滤掉侦察证据。"""
    wanted = set(hosts)
    out: list[dict] = []
    for frag in fragments:
        if frag.get("host") not in wanted:
            continue
        step = frag.get("step", "")
        if not str(step).startswith("recon-"):
            continue
        # real_only 为兼容既有签名而保留；侦察片段按 host 映射后一律保留。
        out.append(dict(frag))
    return out


def check_h1_asset_inventory(assets: list[dict], gaps: list[dict]) -> GateResult:
    missing: list[str] = []
    states: list[str] = []
    for asset in assets:
        for key in ASSET_FIELDS:
            if key not in asset:
                missing.append("资产 %s 缺字段 %s" % (asset.get("asset_id", "?"), key))
        state = asset.get("existence", "")
        if state:
            states.append(state)
    if missing:
        return GateResult("H1", Verdict.BLOCKED, "%d assets" % len(assets), missing)
    return GateResult("H1", Verdict.PASS, "|".join(sorted(set(states))) or "no-state", [])


def check_h2_screenshot(evidence: dict) -> GateResult:
    shot = (evidence.get("screenshot") or "").strip()
    hook = (evidence.get("shot_cmd") or "").strip()
    scored = bool(evidence.get("scored"))
    if scored and not shot:
        return GateResult("H2", Verdict.BLOCKED, "no screenshot file",
                          ["shot_cmd is not a screenshot" if hook else "screenshot missing"])
    return GateResult("H2", Verdict.PASS, shot or "not-scored", [])


def check_h3_dual_channel(dual_cell: str) -> GateResult:
    match = re.search(r"面板=([^；;]+)", dual_cell or "")
    if not match:
        return GateResult("H3", Verdict.BLOCKED, "no panel value", ["panel value missing"])
    panel = match.group(1).strip()
    if panel.startswith(("evidence/", "loot/", "/")) or panel.endswith((".png", ".md")):
        return GateResult("H3", Verdict.BLOCKED, panel,
                          ["screenshot path used as panel flag value"])
    if "截图=" not in dual_cell:
        return GateResult("H3", Verdict.BLOCKED, panel, ["screenshot path missing"])
    return GateResult("H3", Verdict.PASS, panel, [])


def check_h4_reusable_loot(row: dict) -> GateResult:
    status = (row.get("status") or "").strip()
    if status == "失效" or not row.get("asset_id"):
        return GateResult("H4", Verdict.BLOCKED, status or "no asset_id",
                          ["invalid or stale credential must not be reused"])
    return GateResult("H4", Verdict.PASS, status, [])


def check_h5_report_enumeration(report_steps: list[str], recon_steps: list[str],
                                hosts: Iterable[str]) -> GateResult:
    wanted = list(hosts)
    report_set = set(report_steps)
    recon_set = set(recon_steps)
    findings: list[str] = []
    missing = [s for s in recon_steps if s not in report_set]
    if missing:
        findings.append("recon fragments dropped from report: %s" % ", ".join(missing))
    # 每个计分主机在报告中须有侦察证据（枚举段要求），无侦察片段即缺失。
    if wanted and not (recon_set & report_set):
        findings.append("no recon enumeration evidence in report for hosts: %s"
                        % ", ".join(wanted))
    if findings:
        return GateResult("H5", Verdict.BLOCKED, "%d hosts" % len(wanted), findings)
    return GateResult("H5", Verdict.PASS, "%d recon" % len(recon_steps), [])


def check_h6_submission(assets_ok: bool, window_ok: bool, encryption_ok: bool) -> GateResult:
    findings: list[str] = []
    if not assets_ok:
        findings.append("断图检查未通过或未执行")
    if not window_ok:
        findings.append("24h 时间锚缺失或未落盘")
    if not encryption_ok:
        findings.append("归档加密检查命中")
    return GateResult("H6", Verdict.BLOCKED if findings else Verdict.PASS,
                      "submission gate", findings)


ALIGNMENT_CLAIMS: dict[str, str] = {
    "A1": "step_id 贯穿六段交接",
    "A2": "派生索引不新增权威存储",
    "A3": "三份契约均为路径指针",
    "A4": "H1-H6 旁路校验输出 GateResult",
    "A5": "tracer bullet 落在 D11",
    "A6": "零破坏：既有 skill/tool 语义不改",
    "A7": "P0 优先断图/时间锚/加密与双通道字段分离",
    "A8": "可机读对齐矩阵验证无偏离",
}


def verify_alignment(claims: dict[str, str], implemented: set[str]) -> list[str]:
    """返回未实现的条款 ID；空列表表示对齐无偏离。"""
    return [k for k in claims if k not in implemented]


def all_checks(assets: list[dict], gaps: list[dict], evidence: dict, dual_cell: str,
               loot_row: dict, report_steps: list[str], recon_steps: list[str],
               hosts: Iterable[str], submission: tuple[bool, bool, bool]) -> list[GateResult]:
    a, w, e = submission
    return [
        check_h1_asset_inventory(assets, gaps),
        check_h2_screenshot(evidence),
        check_h3_dual_channel(dual_cell),
        check_h4_reusable_loot(loot_row),
        check_h5_report_enumeration(report_steps, recon_steps, hosts),
        check_h6_submission(a, w, e),
    ]
