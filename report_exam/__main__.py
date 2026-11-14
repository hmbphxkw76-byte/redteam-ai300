"""report_exam CLI。

用法（可 copy/paste 复现，§6.1）：
  python -m report_exam index --evidence-dir evidence/attack-ai-agent-real --out host_fragments.json
  python -m report_exam build --evidence-dir evidence/attack-ai-agent-real \
      --out-dir report --osid XXXXX --panel-flags panel.json

`--evidence-dir` 应指向 `-real` 真实证据目录；演练/仿真片段被组装器排除（SKILL §4）。
"""
import argparse
import json
import os
import sys

from ._types import SCORED_HOSTS
from .index import DirEvidenceSource, build_index
from .assemble import assemble_report
from . import EVIDENCE_STEPS


def _load_panel_flags(path):
    if not path:
        return None
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def cmd_index(args):
    model = build_index(DirEvidenceSource(args.evidence_dir),
                        expected_hosts=list(SCORED_HOSTS), osid=args.osid,
                        panel_flags=_load_panel_flags(args.panel_flags))
    payload = {h: [f.step_id for f in fs] for h, fs in model.hosts.items()}
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    print("已生成证据索引：%s（%d 主机）" % (args.out, len(payload)))
    print("证据步骤契约：%s" % ", ".join(EVIDENCE_STEPS))
    print("未达成主机：%s" % ", ".join(h for h, fs in model.hosts.items() if not fs))
    return 0


def cmd_build(args):
    result = assemble_report(
        DirEvidenceSource(args.evidence_dir),
        expected_hosts=list(SCORED_HOSTS),
        osid=args.osid,
        panel_flags=_load_panel_flags(args.panel_flags),
        out_dir=args.out_dir,
        do_package=not args.no_package,
    )
    os.makedirs(args.out_dir, exist_ok=True)
    with open(os.path.join(args.out_dir, "report-EN.md"), "w", encoding="utf-8") as f:
        f.write(result["en"])
    with open(os.path.join(args.out_dir, "report-ZH.md"), "w", encoding="utf-8") as f:
        f.write(result["zh"])
    print("四章骨架 + official 主机小节 + 双版已写入 %s" % args.out_dir)
    print("证据步骤契约：%s" % ", ".join(result["evidence_steps"]))
    for k, v in sorted(result["ac"].items()):
        print("  %s: %s" % (k, "PASS" if v else "MISS"))
    # 打包成功后以 package 的最终 verify 为准；否则沿用 dry-run 的内容校验结果，
    # 避免「submission-ready: yes」与 dry-run 的 VG-3 核实闸同时出现（T06 修复项）。
    final = result["package"]["verify"] if result["package"] else result["verify"]
    print("verify-evidence: %s" % ("passed" if final["passed"] else "blocked"))
    if result["submission_ready"]:
        print("submission-ready: yes")
    else:
        print("submission-ready: %s" % ("no (详见下方阻断项)" if result["package"]
                                      else "no (dry-run / VG-3)"))
    for m in final["missing"][:5]:
        print("  [待补录] %s" % m)
    for p in final["pending"][:5]:
        print("  [核实闸] %s" % p)
    if result["package"] is not None and not result["package"]["passed"]:
        for b in result["package"]["blocking"]:
            print("  [阻断] %s" % b, file=sys.stderr)
        return 1
    return 0 if result["verify"]["passed"] else 1


def main(argv=None):
    ap = argparse.ArgumentParser(description="OSAI 官方报告组装器")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p_idx = sub.add_parser("index", help="构建主机→证据片段索引")
    p_idx.add_argument("--evidence-dir", required=True, help="真实证据目录（含 -real）")
    p_idx.add_argument("--out", required=True)
    p_idx.add_argument("--osid", default="XXXXX")
    p_idx.add_argument("--panel-flags", help="控制面板提交值 JSON（§6.2 双通道）")
    p_idx.set_defaults(func=cmd_index)

    p_bld = sub.add_parser("build", help="组装报告并跑 verify-evidence")
    p_bld.add_argument("--evidence-dir", required=True, help="真实证据目录（含 -real）")
    p_bld.add_argument("--out-dir", required=True)
    p_bld.add_argument("--osid", default="XXXXX")
    p_bld.add_argument("--panel-flags", help="控制面板提交值 JSON（§6.2 双通道）")
    p_bld.add_argument("--no-package", action="store_true",
                       help="dry-run：跳过 pandoc/7z（转 VG-3 核实闸，不可提交）")
    p_bld.set_defaults(func=cmd_build)

    args = ap.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
