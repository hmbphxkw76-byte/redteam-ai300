#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""编排：sc-01~sc-08 顺序派发（阶段8 tracer bullet）。

`run(step, ctx)` 依 step 路由到 seam 调用；未知 step 报错。仅编排，不含攻击逻辑。
"""
STEP_IDS = ("sc-01", "sc-02", "sc-03", "sc-04", "sc-05", "sc-06", "sc-07", "sc-08")


def _sc01(ctx):
    from .recon_input import load_assets
    return load_assets(ctx["assets_path"])


def _sc02(ctx):
    from .poison_engine import poison_dataset
    return poison_dataset(ctx["data"], ctx["trigger"], ctx.get("target", ""),
                          ctx.get("frac", 0.01), ctx.get("backend"))


def _sc03(ctx):
    from .poison_engine import poison_model
    return poison_model(ctx["base"], ctx["adapter_out"], ctx["trigger"], ctx.get("backend"))


def _sc04(ctx):
    from .injector import inject_pipeline
    return inject_pipeline(ctx["pipeline"], ctx.get("stage", "preprocess"), ctx["inject"])


def _sc05(ctx):
    from .injector import inject_dependency
    return inject_dependency(ctx["index"], ctx["pkg"], ctx["malicious"])


def _sc06(ctx):
    from .injector import inject_build
    return inject_build(ctx["build"], ctx["payload"])


def _sc07(ctx):
    from .evidence import emit
    return emit("sc-07", ctx["cmd"], ctx["out"], ai_log=ctx.get("ai_log"),
                target=ctx.get("target"), runner=ctx.get("runner"))


def _sc08(ctx):
    from .evidence import emit
    return emit("sc-08", ctx["cmd"], ctx["out"], flag=ctx.get("flag"),
                ai_log=ctx.get("ai_log"), target=ctx.get("target"),
                runner=ctx.get("runner"))


_DISPATCH = {"sc-01": _sc01, "sc-02": _sc02, "sc-03": _sc03, "sc-04": _sc04,
             "sc-05": _sc05, "sc-06": _sc06, "sc-07": _sc07, "sc-08": _sc08}


def run(step, ctx):
    handler = _DISPATCH.get(step)
    if handler is None:
        raise ValueError("未知 step: %r（应为 %s 之一）" % (step, ", ".join(STEP_IDS)))
    return handler(ctx)
