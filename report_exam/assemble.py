"""报告组装器公开入口（Seam-1 唯一注入点）。

编排：素材聚合 → 四章骨架（official 小节注入五段式）→ AI 附录 → 双版
→ 打包/verify-evidence 提交前置。不重新取证、不虚构利用过程、不调用 PyRIT。
"""
from ._types import SCORED_HOSTS
from .index import build_index
from .bilingual import render_bilingual, extract_facts
from .package import package, verify_report
from .sections import render_all_host_sections, render_host_body
from .ai_appendix import collect_ai_logs
from . import EVIDENCE_STEPS


def assemble_report(evidence_source, expected_hosts=None, osid="XXXXX",
                    panel_flags=None, out_dir=None, runner=None,
                    do_package=True):
    """组装完整报告并返回结构化结果（供 CI/测试机读判定）。

    - evidence_source: Seam-1 注入点（DirEvidenceSource / MemoryEvidenceSource）
    - panel_flags: 控制面板提交值 {host: flag}，§6.2 双通道比对的输入
    - runner: 注入 subprocess 执行器（pandoc/7z 可测）
    - do_package: False 为 dry-run（不产物、不可提交，vrf-07 记未判定）
    """
    model = build_index(evidence_source, expected_hosts=expected_hosts,
                        osid=osid, panel_flags=panel_flags)
    frags = [f for fs in model.hosts.values() for f in fs]

    en, zh = render_bilingual(model)
    host_sections = render_all_host_sections(model)
    appendix_d = collect_ai_logs(frags)
    facts_equal = bool(extract_facts(en)) and extract_facts(en) == extract_facts(zh)

    verify = verify_report(model, en, appendix_md=appendix_d)
    pkg = package(model, en, out_dir, runner=runner) if (do_package and out_dir) else None

    missing_hosts = [h for h, fs in model.hosts.items() if not fs]
    canonical = set(expected_hosts or SCORED_HOSTS)

    ac = {
        "AC-01": set(model.hosts) == canonical,
        "AC-02": all("NOT ATTEMPTED" in render_host_body(h, model.hosts[h])
                     for h in missing_hosts),
        "AC-03": all(a in en for a in [
            "## Introduction", "## Objective", "## Requirements",
            "# Executive Summary", "# Attack Walkthrough", "# Appendix"]),
        "AC-04": "Offsec AI Red Teamer Report" in en,
        "AC-05": all(a in en for a in [
            "#### Initial Access / Exploitation",
            "#### Privilege Escalation (if applicable)", "#### Proof",
            "#### Evidence Attribution", "**Enumeration**",
            "**Vulnerability & Full Exploitation**"]),
        "AC-06": all((f.command in en and f.output in en) for f in frags
                     if f.command and f.output),
        "AC-07": all(f.ai_log.strip() in appendix_d for f in frags if f.ai_log.strip()),
        "AC-08": verify["checks"]["vrf-04"] is True,
        "AC-09": verify["checks"]["proof-single"] is True,
        "AC-10": facts_equal,
        "AC-11": ("## A. Scripts & PoC" in en and "see Appendix A" in en),
        "AC-12": bool(pkg and pkg["verify"]["checks"]["vrf-07"] is True) if pkg else False,
        "AC-13": bool(pkg and pkg["passed"]) if pkg else verify["passed"],
        "AC-14": ("Intentionally Not Vulnerable Hosts" in en
                  and en.count("confirmed not exploitable") >= 2
                  and en.count("确认不可利用") >= 2),
        "AC-15": (all((f.source_path or f.step_id) in en for f in frags)
                  if frags else True),
    }

    return {
        "model": model,
        "en": en,
        "zh": zh,
        "host_sections": host_sections,
        "appendix_d": appendix_d,
        "facts_equal": facts_equal,
        "evidence_steps": EVIDENCE_STEPS,
        "verify": verify,
        "package": pkg,
        "ac": ac,
        "submission_ready": bool(pkg and pkg["passed"]),
        "all_ac_pass": all(ac.values()),
    }
