#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""对话面攻击 CLI：形态适配 + 策略库 + 评分链（方案 P2/P3/P4/P5 的统一入口）。

    python -m tools.attack_ai_agent.dialogue_cli --list-strategies
    python -m tools.attack_ai_agent.dialogue_cli --target http://<HOST>:7002 \\
        --endpoint-template chat --strategy S-ANCHOR --repeat 3 --json

与既有入口的分工：
  - `run_real.py`：AIVP 形态的 11 步技能主线（需 pyrit + 双模型）
  - `dialogue_cli.py`：任意对话形态 + 策略库驱动，无需 pyrit 即可运行
"""
import argparse
import json
import sys
from typing import Dict, List

from tools.attack_ai_agent import dialogue, strategies


def _parse_args(argv=None):
    ap = argparse.ArgumentParser(
        description="对话面攻击：策略库驱动 + 否定语境守卫评分")
    ap.add_argument("--target", default="", help="目标基址，如 http://<HOST>:7002")
    ap.add_argument("--endpoint-template", default="chat",
                    choices=sorted(dialogue.PRESETS), help="请求形态预置")
    ap.add_argument("--path", default="", help="覆盖形态路径（如 /chat）")
    ap.add_argument("--body-template", default="",
                    help='覆盖请求体模板，用 {PROMPT} 占位，如 {"message": "{PROMPT}"}')
    ap.add_argument("--response-field", default=None,
                    help='覆盖响应取值字段；传空串表示取整段文本')
    ap.add_argument("--lab", default="", help="替换 {lab} 占位")
    ap.add_argument("--agent", default="", help="替换 {agent} 占位")
    ap.add_argument("--strategy", action="append", default=[],
                    help="策略 ID，可重复；缺省为全部 proven")
    ap.add_argument("--status", default="proven",
                    choices=("proven", "unstable", "refuted", "unproven", ""),
                    help="按状态筛选（--strategy 优先）")
    ap.add_argument("--repeat", type=int, default=1, help="每条策略重复次数")
    ap.add_argument("--timeout", type=int, default=90, help="单轮超时秒数")
    ap.add_argument("--semantic", action="store_true",
                    help="启用 PyRIT 语义评分器（第二道，只否决）")
    ap.add_argument("--multiturn", default="",
                    help="启用 PyRIT 多轮攻击类（传类名或 auto）")
    ap.add_argument("--turns", type=int, default=3, help="多轮攻击的最大轮数")
    ap.add_argument("--strategies-file", default="", help="策略库路径")
    ap.add_argument("--list-strategies", action="store_true", help="打印策略表后退出")
    ap.add_argument("--json", action="store_true", help="输出 JSON")
    ap.add_argument("--out", default="", help="把 JSON 结果写入文件")
    return ap.parse_args(argv)


def _build_spec(args) -> dialogue.ChatSpec:
    spec = dialogue.PRESETS[args.endpoint_template]
    return dialogue.ChatSpec(
        label=spec.label,
        method=spec.method,
        path=args.path or spec.path,
        body_template=args.body_template or spec.body_template,
        response_field=(spec.response_field if args.response_field is None
                        else args.response_field),
    )


def _semantic_fn(args):
    """构造语义否决器；不可用时返回 (None, 诊断)，不静默忽略。"""
    if not args.semantic:
        return None, "未启用"
    from tools.attack_ai_agent import pyrit_semantic
    return pyrit_semantic.make_refusal_veto()


def _run_strategy(strategy, spec, args, semantic):
    """执行一条策略的 N 次重复；判定取每次的最后一条响应。"""
    runs: List[Dict[str, object]] = []
    for index in range(max(1, args.repeat)):
        turns = []
        for message in strategy.steps:
            turn = dialogue.send(args.target, spec, message,
                                 timeout=args.timeout,
                                 lab=args.lab, agent=args.agent)
            turns.append(turn.as_dict())
            if turn.error:
                break
        last = turns[-1]["response"] if turns else ""
        chain = dialogue.score(str(last), strategy.pattern,
                               semantic=semantic,
                               require_affirmative=strategy.require_affirmative,
                               objective=strategy.rationale)
        runs.append({
            "strategy_id": strategy.id,
            "repeat": index + 1,
            "turns": turns,
            "chain": chain.as_dict(),
            "effective": chain.effective,
        })
    return runs


def main(argv=None):
    args = _parse_args(argv)
    library = strategies.load(args.strategies_file or None)
    if args.list_strategies:
        print(strategies.render_table(library))
        return 0
    if not library:
        print("策略库为空或不可读：%s" % (args.strategies_file or strategies.DEFAULT_PATH))
        return 2
    if not args.target:
        print("缺少 --target")
        return 2

    selected = strategies.select(library, args.strategy, args.status or "")
    if not selected:
        print("未选中任何策略（检查 --strategy / --status）")
        return 2

    spec = _build_spec(args)
    semantic, semantic_diag = _semantic_fn(args)

    report: Dict[str, object] = {
        "target": args.target,
        "chat_spec": spec.to_dict(),
        "semantic": semantic_diag,
        "runs": [],
    }
    for strategy in selected:
        report["runs"].extend(_run_strategy(strategy, spec, args, semantic))

    if args.multiturn:
        from tools.attack_ai_agent import pyrit_multiturn
        attacks = pyrit_multiturn.available_attacks()
        name = "" if args.multiturn == "auto" else args.multiturn
        picked = pyrit_multiturn.run_multiturn(
            objective=selected[0].steps[0], chat_spec=spec, base_url=args.target,
            attack_name=name, max_turns=max(2, args.turns),
            timeout=args.timeout, lab=args.lab, agent=args.agent)
        report["multiturn"] = picked.as_dict()
        report["multiturn"]["available_attacks"] = sorted(attacks)

    report["aggregate"] = strategies.aggregate(report["runs"])

    if args.out:
        with open(args.out, "w", encoding="utf-8") as handle:
            json.dump(report, handle, ensure_ascii=False, indent=1)

    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=1))
        return 0

    print("target=%s spec=%s(%s) semantic=%s" % (
        args.target, spec.label, spec.path, semantic_diag))
    for run in report["runs"]:
        chain = run["chain"]
        print("%-16s #%d effective=%-5s %s" % (
            run["strategy_id"], run["repeat"], run["effective"],
            (chain.get("judgement") or {}).get("reason", "")[:56]))
    print("\n聚合：")
    for sid, row in sorted(report["aggregate"].items()):
        print("  %-16s %d/%d = %.0f%%" % (sid, row["effective"],
                                          row["attempts"], row["rate"] * 100))
    if "multiturn" in report:
        mt = report["multiturn"]
        print("\n多轮：%s executed=%s %s" % (mt.get("attack_name"),
                                            mt.get("executed"), mt.get("reason")))
    return 0


if __name__ == "__main__":
    sys.exit(main())
