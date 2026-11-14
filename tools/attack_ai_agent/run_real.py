#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""真实双模型攻击运行器（生产 seam，需 pyrit==1.1.0 与 .env 凭据）。

职责（对齐用户 2026-11-14 双模型要求）：
  1. 攻击 / 目标模型：OPENAI_CHAT_* 命名空间（默认模型，类似 workbuddy 提供的模型）。
     - 当 --target http（默认）：通过 HTTPTarget 对接 OWASP AIVP 靶机
       http://192.168.40.189/api/labs/{lab_id}/chat（靶机后端模型即 LongCat-2.5）。
     - 当 --target openai：直接以 OPENAI_CHAT_* 模型作为被攻击目标。
  2. 评分模型：OPENAI_SCORER_* 命名空间，独立 OpenAIChatTarget 实例，
     注入 SelfAskTrueFalseScorer，与攻击模型职责清晰分离。

凭据加载：本脚本自动读取仓库根目录 .env（gitignored，含真实值），
        并回退到已 export 的环境变量；二者皆无则报错退出。
        因此同一份脚本在任意环境、任意会话均可直接运行，无需重复设置。

用法：
  py tools/attack_ai_agent/run_real.py --lab MM_04 --paths A C
  py tools/attack_ai_agent/run_real.py --target openai --paths A
  py tools/attack_ai_agent/run_real.py --lab MM_04 --step aia-02
"""
import argparse
import os
import sys
import time

if __package__ in (None, ""):
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(
        os.path.abspath(__file__)))))
    from tools.attack_ai_agent import runner
    from tools.attack_ai_agent.backends import RealPyRITBackend
    from tools.attack_ai_agent.steps import STEP_SPECS
else:
    from . import runner
    from .backends import RealPyRITBackend
    from .steps import STEP_SPECS

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def load_dotenv(path):
    """手动加载 .env（不依赖 python-dotenv）；仅在变量未设置时写入，显式 env 优先。"""
    if not os.path.exists(path):
        return 0
    n = 0
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, val = line.partition("=")
            key, val = key.strip(), val.strip()
            if key and key not in os.environ:
                os.environ[key] = val
                n += 1
    return n


def require_env():
    needed = ("OPENAI_CHAT_KEY", "OPENAI_CHAT_ENDPOINT", "OPENAI_CHAT_MODEL",
              "OPENAI_SCORER_KEY", "OPENAI_SCORER_ENDPOINT", "OPENAI_SCORER_MODEL")
    missing = [k for k in needed if not os.environ.get(k)]
    if missing:
        sys.stderr.write("缺少必需环境变量：%s\n" % ", ".join(missing))
        sys.exit(2)
    # 显式校验两命名空间指向不同模型可独立替换（当前允许相同端点，仅校验存在）
    print("攻击/目标模型  OPENAI_CHAT_*  = %s @ %s" % (
        os.environ["OPENAI_CHAT_MODEL"], os.environ["OPENAI_CHAT_ENDPOINT"]))
    print("评分模型       OPENAI_SCORER_* = %s @ %s" % (
        os.environ["OPENAI_SCORER_MODEL"], os.environ["OPENAI_SCORER_ENDPOINT"]))


def main(argv=None):
    ap = argparse.ArgumentParser(description="attack-ai-agent 真实双模型运行器")
    ap.add_argument("--lab", default="MM_04", help="AIVP 靶机实验室 ID（MM_04/05/07）")
    ap.add_argument("--host", default="192.168.40.189",
                    help="AIVP 靶机地址（http）")
    ap.add_argument("--target", default="http", choices=("http", "openai"),
                    help="被攻击目标形态：http=靶机 HTTP 端点；openai=直接 LLM 模型")
    ap.add_argument("--paths", default="A C", help="执行路径，空格分隔，如 'A C'")
    ap.add_argument("--step", default="", help="仅执行单个步骤，如 aia-02")
    ap.add_argument("--evidence-dir", default="", help="证据片段输出目录")
    args = ap.parse_args(argv)

    loaded = load_dotenv(os.path.join(ROOT, ".env"))
    require_env()

    target_config = {
        "kind": args.target,
        "lab_id": args.lab,
        "host": args.host,
    }
    backend = RealPyRITBackend(target_config=target_config)
    print("后端：%s" % backend.describe())

    specs = list(STEP_SPECS)
    if args.step:
        specs = [s for s in specs if s.step_id == args.step]
        if not specs:
            sys.stderr.write("未知步骤：%s\n" % args.step)
            sys.exit(2)
    else:
        wanted = set(args.paths.split())
        path_steps = {
            "A": ("aia-01", "aia-02", "aia-03", "aia-04"),
            "B": ("aia-05", "aia-06", "aia-07"),
            "C": ("aia-08", "aia-09", "aia-10"),
        }
        keep = set()
        for p in wanted:
            keep.update(path_steps.get(p, ()))
        # 注：aia-11/12 为「立足后 flag 取证」步骤，需真实取得 ai_vector.txt 才落盘；
        # 真实靶机运行若未实际获取 flag，不强制纳入，避免注入演示占位 flag。
        specs = [s for s in specs if s.step_id in keep]

    out_dir = args.evidence_dir or os.path.join(ROOT, "evidence", "attack-ai-agent-real")
    os.makedirs(out_dir, exist_ok=True)

    target_label = ("http://%s/api/labs/%s/chat" % (args.host, args.lab)
                    if args.target == "http" else "OPENAI_CHAT_* (direct model)")

    print("目标：%s　步骤数：%d" % (target_label, len(specs)))
    ok = 0
    for spec in specs:
        graph = runner.graph_for_step(spec.step_id)
        t0 = time.time()
        resp = backend.execute(spec.step_id, spec.objective)
        level = runner.grade(resp) if hasattr(runner, "grade") else resp.verdict
        el = time.time() - t0
        # 真实证据落盘（复用 run_attack 的 emit_evidence 与 --strict 质量门）
        path = runner.emit_evidence(spec, resp, level, graph, target_label, out_dir)
        ok += 1
        print("  %s [%s] 决定性=%s LLM线索=%s 耗时=%.1fs → %s" % (
            spec.step_id, level, resp.deterministic_hit, resp.llm_hit, el,
            os.path.basename(path)))
    print("完成：%d/%d 步骤已执行并落盘证据于 %s" % (ok, len(specs), out_dir))
    return 0


if __name__ == "__main__":
    sys.exit(main())
