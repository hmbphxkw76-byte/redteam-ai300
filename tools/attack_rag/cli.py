#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""命令行入口（薄壳）：单步或全量执行，落盘证据并打印结论。

示例（离线合成 harness，CI/复现用）：
  python tools/attack_rag/cli.py --step rag-00 --backend fake
  python tools/attack_rag/cli.py --path A --path B --path C --backend fake

示例（真实摄取通道 / recon 清单 / 已知只读）：
  python tools/attack_rag/cli.py --step rag-01 --rag-writable no
  python tools/attack_rag/cli.py --path A --ingest-url http://<RAG_INGEST>
  python tools/attack_rag/cli.py --step rag-00 --recon-inventory loot/recon-ai.json
  python tools/attack_rag/cli.py --step rag-05 --whoami 'uid=1000(rag)' \
      --flag-panel <面板值> --flag-shot <截图值>

退出码：0 成功（含「已跳过」）；1 证据质量门失败；2 用法错误。
"""
import argparse
import json
import os
import sys
from dataclasses import replace

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if ROOT not in sys.path:  # 支持 `python tools/attack_rag/cli.py` 直跑
    sys.path.insert(0, ROOT)

from tools.attack_rag import Runtime, run_attack  # noqa: E402
from tools.attack_rag.ingest import read_doc  # noqa: E402
from tools.attack_rag.model import AttackRequest  # noqa: E402
from tools.attack_rag.runner import DEFAULT_EVIDENCE_DIR  # noqa: E402
from tools.attack_rag.steps import STEP_IDS  # noqa: E402


def build_parser():
    ap = argparse.ArgumentParser(description="RAG 投毒与检索层操纵执行器（attack-rag）")
    ap.add_argument("--target", default="rag-harness", help="目标标识（演练目标或合成 harness）")
    ap.add_argument("--backend", choices=("fake", "real"), default="fake",
                    help="fake=离线确定性（CI 默认）；real=目标 PyRIT 版本 + 端点（见 tools/pyrit_compat）")
    ap.add_argument("--path", action="append", choices=("A", "B", "C"), default=None,
                    help="攻击路径（可重复）；缺省全选")
    ap.add_argument("--step", default="", help="仅执行单步：%s" % ", ".join(STEP_IDS))
    ap.add_argument("--corpus-size", type=int, default=1200, help="合成语料规模（≥1000 满足 ASR 前提）")
    ap.add_argument("--k", type=int, default=3, help="top-k")
    ap.add_argument("--query", default=None, help="目标查询（缺省用内置样例）")
    ap.add_argument("--answer", default=None, help="注入答案（条件 2）")
    ap.add_argument("--recon-inventory", default="",
                    help="recon-ai 资产清单 JSON（前置定位用；缺省退化为合成面）")
    ap.add_argument("--ingest-url", default="", help="<RAG_INGEST> 摄取端点（真实写入通道）")
    ap.add_argument("--ingest-doc", default="", help="待注入文档路径（缺省用构造载荷）")
    ap.add_argument("--ingest-content-type", choices=("json", "form"), default="json",
                    help="摄取载荷形态：json（默认）或表单编码")
    ap.add_argument("--ingest-title-field", default="", help="表单摄取的标题字段名")
    ap.add_argument("--ingest-content-field", default="", help="表单摄取的正文字段名")
    ap.add_argument("--rag-writable", choices=("yes", "no", "unknown"), default="unknown",
                    help="目标 RAG 可写判定；no 时按「失败与豁免」降级为间接注入")
    ap.add_argument("--downstream-coupled", choices=("yes", "no", "unknown"),
                    default="unknown", help="下游 agent 是否消费检索结果；no 时记「未产生影响」")
    ap.add_argument("--index-access", action="store_true",
                    help="已取得向量库写权限：演示直接操纵索引权重/元数据排序")
    ap.add_argument("--whoami", default="", help="立足点访问证明实测值（whoami/id 输出）")
    ap.add_argument("--evidence-dir", default=DEFAULT_EVIDENCE_DIR, help="证据片段输出目录")
    ap.add_argument("--no-emit", action="store_true", help="不落盘证据（仅取结论）")
    ap.add_argument("--flag-panel", default="", help="flag 双通道之一：控制面板提交值")
    ap.add_argument("--flag-shot", default="", help="flag 双通道之二：截图/正文中的值")
    ap.add_argument("--flag-oracle", default="", help="校验预言机回执（flag 缺席时等价通道）")
    ap.add_argument("--json", action="store_true", help="输出机读 JSON 报告")
    return ap


def main(argv=None, runtime=None):
    """命令行主函数；`runtime` 可注入（测试替身即离线）。"""
    args = build_parser().parse_args(argv)
    try:
        ingest_doc = read_doc(args.ingest_doc) if args.ingest_doc else ""
    except ValueError as exc:
        print("ERROR: %s" % exc, file=sys.stderr)
        return 2
    request = AttackRequest(
        target=args.target, corpus_size=args.corpus_size, k=args.k,
        paths=tuple(args.path or ("A", "B", "C")), step=args.step,
        evidence_dir=args.evidence_dir, emit=not args.no_emit,
        backend=args.backend, flag_panel=args.flag_panel,
        flag_shot=args.flag_shot, flag_oracle=args.flag_oracle,
        recon_inventory=args.recon_inventory, ingest_url=args.ingest_url,
        ingest_doc=ingest_doc,
        ingest_content_type=("application/x-www-form-urlencoded"
                             if args.ingest_content_type == "form"
                             else "application/json"),
        ingest_title_field=args.ingest_title_field,
        ingest_content_field=args.ingest_content_field,
        rag_writable=args.rag_writable,
        downstream_coupled=args.downstream_coupled,
        index_access=args.index_access, whoami=args.whoami)
    if args.query:
        request = replace(request, query=args.query)
    if args.answer:
        request = replace(request, answer=args.answer)
    try:
        report = run_attack(request, runtime)
    except ValueError as exc:
        print("ERROR: %s" % exc, file=sys.stderr)
        return 2
    except RuntimeError as exc:
        print("ERROR: %s" % exc, file=sys.stderr)
        return 1

    if args.json:
        print(json.dumps(report.as_dict(), ensure_ascii=False, indent=1))
        return 0

    print("目标：%s　后端：%s　flag：%s"
          % (request.target, report.backend, report.flag.describe()))
    print("%-8s %-5s %-8s %s" % ("步骤", "路径", "效果", "依据"))
    for v in report.verdicts:
        print("%-8s %-5s %-8s %s" % (v.step_id, v.path or "—", v.level, v.reason))
        if v.evidence_path:
            print("         证据：%s" % v.evidence_path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
