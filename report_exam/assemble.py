"""报告组装器公开入口（Seam-1 唯一注入点）。

assemble_report(evidence_source, ...) 编排：
素材聚合 → 四章骨架 → 每主机五段式 → AI 附录 → 双版 → 打包/校验。
不重新取证、不虚构利用过程、不调用 PyRIT。
"""
from .index import build_index
from .bilingual import render_bilingual, extract_facts
from .package import package, verify_report
from .sections import render_all_host_sections, render_host_section
from .ai_appendix import collect_ai_logs


def assemble_report(evidence_source, expected_hosts=None, osid="XXXXX",
                    out_dir=None, runner=None, do_package=True):
    """组装完整报告并返回结构化结果（供 CI/测试机读判定）。

    参数
    - evidence_source: Seam-1 注入点，实现 iter_fragments()（默认 DirEvidenceSource）
    - expected_hosts: 计分目标全集（用于 AC-01 覆盖与 AC-02 未达成回溯）
    - runner: 注入 subprocess 执行器（package 阶段惰性工具可测）
    - do_package: False 时跳过 pandoc/7z（沙箱无工具，转 VG-3 核实闸）

    返回 dict：model / en / zh / host_sections / appendix_d / facts_equal /
               verify / package / ac（AC-01..15 逐项布尔）。
    """
    model = build_index(evidence_source, expected_hosts=expected_hosts, osid=osid)
    frags = [f for fs in model.hosts.values() for f in fs]

    en, zh = render_bilingual(model)
    host_sections = render_all_host_sections(model)
    appendix_d = collect_ai_logs(frags)
    facts_equal = bool(extract_facts(en)) and extract_facts(en) == extract_facts(zh)

    verify = verify_report(model, en, appendix_md=appendix_d)
    pkg = package(model, en, out_dir, runner=runner) if (do_package and out_dir) else None

    missing_hosts = [h for h, fs in model.hosts.items() if not fs]

    ac = {
        # AC-01 素材聚合无遗漏
        "AC-01": (not expected_hosts) or set(model.hosts) >= set(expected_hosts),
        # AC-02 缺失回溯记 NOT ATTEMPTED / 未达成 且不虚构
        "AC-02": all("NOT ATTEMPTED" in render_host_section(h, model.hosts[h], lang="en")
                     or "未达成" in render_host_section(h, model.hosts[h], lang="zh")
                     for h in missing_hosts),
        # AC-03 四章齐全
        "AC-03": all(a in en for a in [
            "## Introduction", "## Objective", "## Requirements",
            "# Executive Summary", "# Attack Walkthrough", "# Appendix"]),
        # AC-04 TOC 条目（pandoc --toc 据此生成目录）
        "AC-04": "Offsec AI Red Teamer Report" in en,
        # AC-05 每主机五段式
        "AC-05": ("#### Initial Access / Exploitation" in host_sections
                  and "#### Proof" in host_sections),
        # AC-06 无损 include：命令/输出逐字出现
        "AC-06": all((f.command in en and f.output in en) for f in frags
                     if f.command and f.output),
        # AC-07 AI 交互日志全量入 Appendix D
        "AC-07": all(f.ai_log.strip() in appendix_d for f in frags if f.ai_log.strip()),
        # AC-08 flag 双通道占位
        "AC-08": verify["checks"]["vrf-04"],
        # AC-09 proof.txt 单次
        "AC-09": verify["checks"]["proof-single"],
        # AC-10 双版事实逐字一致
        "AC-10": facts_equal,
        # AC-11 长 PoC 分流位（Appendix A）
        "AC-11": "## A. Scripts & PoC" in en,
        # AC-12 命名与归档合规（未打包时为 False，转 VG-3）
        "AC-12": bool(pkg and pkg["verify"]["checks"]["vrf-07"]) if pkg else False,
        # AC-13 verify-evidence 衔接
        "AC-13": bool(pkg and pkg["passed"]) if pkg else verify["passed"],
        # AC-14 诱饵机小节存在
        "AC-14": "Intentionally Not Vulnerable Hosts" in en,
        # AC-15 证据归属可溯
        "AC-15": (all((f.source_path or f.step_id) in host_sections for f in frags)
                  if frags else True),
    }

    return {
        "model": model,
        "en": en,
        "zh": zh,
        "host_sections": host_sections,
        "appendix_d": appendix_d,
        "facts_equal": facts_equal,
        "verify": verify,
        "package": pkg,
        "ac": ac,
        "all_ac_pass": all(ac.values()),
    }
