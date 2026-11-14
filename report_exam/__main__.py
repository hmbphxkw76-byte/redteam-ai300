"""report_exam CLI。

用法（可 copy/paste 复现，§6.1）：
  python -m report_exam index --evidence-dir evidence --out host_fragments.json
  python -m report_exam build --evidence-dir evidence --out-dir report --osid XXXXX
"""
import argparse
import json
import os
import sys

from .index import DirEvidenceSource, build_index
from .assemble import assemble_report

DEFAULT_EXPECTED_HOSTS = [
    "chain1-host1", "chain1-host2", "chain1-host3",
    "chain2-host1", "chain2-host2", "chain2-host3",
    "standalone", "domain-controller",
]


def cmd_index(args):
    model = build_index(DirEvidenceSource(args.evidence_dir),
                        expected_hosts=DEFAULT_EXPECTED_HOSTS, osid=args.osid)
    payload = {h: [f.step_id for f in fs] for h, fs in model.hosts.items()}
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    print("已生成证据索引：%s（%d 主机）" % (args.out, len(payload)))
    print("未达成主机：%s" % ", ".join(h for h, fs in model.hosts.items() if not fs))
    return 0


def cmd_build(args):
    result = assemble_report(
        DirEvidenceSource(args.evidence_dir),
        expected_hosts=DEFAULT_EXPECTED_HOSTS,
        osid=args.osid,
        out_dir=args.out_dir,
        do_package=not args.no_package,
    )
    os.makedirs(args.out_dir, exist_ok=True)
    with open(os.path.join(args.out_dir, "report-EN.md"), "w", encoding="utf-8") as f:
        f.write(result["en"])
    with open(os.path.join(args.out_dir, "report-ZH.md"), "w", encoding="utf-8") as f:
        f.write(result["zh"])
    print("四章骨架 + 五段式 + 双版已写入 %s" % args.out_dir)
    for k, v in sorted(result["ac"].items()):
        print("  %s: %s" % (k, "PASS" if v else "MISS"))
    print("verify-evidence: %s" % ("passed" if result["verify"]["passed"] else "blocked"))
    for m in result["verify"]["missing"][:5]:
        print("  [待补录] %s" % m)
    return 0 if result["verify"]["passed"] else 1


def main(argv=None):
    ap = argparse.ArgumentParser(description="OSAI 官方报告组装器")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p_idx = sub.add_parser("index", help="构建主机→证据片段索引")
    p_idx.add_argument("--evidence-dir", required=True)
    p_idx.add_argument("--out", required=True)
    p_idx.add_argument("--osid", default="XXXXX")
    p_idx.set_defaults(func=cmd_index)

    p_bld = sub.add_parser("build", help="组装报告并跑 verify-evidence")
    p_bld.add_argument("--evidence-dir", required=True)
    p_bld.add_argument("--out-dir", required=True)
    p_bld.add_argument("--osid", default="XXXXX")
    p_bld.add_argument("--no-package", action="store_true",
                       help="跳过 pandoc/7z（沙箱无工具时转 VG-3 核实闸）")
    p_bld.set_defaults(func=cmd_build)

    args = ap.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
