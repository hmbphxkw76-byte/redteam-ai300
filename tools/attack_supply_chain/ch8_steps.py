#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""S6 课件攻击链独立步骤注册表（sc-09..sc-14）。

关键约束：不注入 workflow.STEP_IDS（既有夹具 len==8 必须保持）；仅本表派发。
sc-09 G1 MCP源码后门；sc-10 G2 Pickle RCE；sc-11 G4/G5 投毒放大；
sc-12 G6 LoRA；sc-13 G7 Tokenizer；sc-14 G8 Pickle绕过。
"""
STEP_IDS_CH8 = ("sc-09", "sc-10", "sc-11", "sc-12", "sc-13", "sc-14")


def run_ch8(step, ctx):
    """按步骤标识派发到对应模块；未知步骤报错。"""
    if step == "sc-09":
        from .mcp_backdoor import build_plan
        return build_plan(ctx["server"], ctx["helper"], ctx["author"], ctx["email"])
    if step == "sc-10":
        from .pickle_rce import build_plan
        return build_plan(ctx["base"], ctx["epoch"], ctx.get("cmd", "id"))
    if step == "sc-11":
        from .amplification import build_poison_set
        return build_poison_set(ctx["samples"], ctx.get("base_lines", 74),
                                ctx.get("factor", 10))
    if step == "sc-12":
        from .adapter_poison import build_plan
        return build_plan(ctx.get("config", {}), ctx.get("text", ""), ctx["ip"])
    if step == "sc-13":
        from .tokenizer_swap import build_plan
        return build_plan(ctx["vocab"], ctx["fast"])
    if step == "sc-14":
        from .pickle_bypass import variant_table
        return variant_table()
    raise ValueError("未知 Ch8 step: %r（应为 %s 之一）" % (step, ", ".join(STEP_IDS_CH8)))


def main(argv=None):
    import argparse, json
    p = argparse.ArgumentParser(description="S6 Ch8 独立步骤注册表")
    p.add_argument("--list", action="store_true")
    a = p.parse_args(argv)
    if a.list:
        print(json.dumps(list(STEP_IDS_CH8)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
