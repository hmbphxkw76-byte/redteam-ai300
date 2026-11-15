#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""标准库行覆盖率测量（CI-CD §3 S2 / 阶段 9 门禁复现命令）。

零外部依赖：用 `code.co_lines()` 取真实可执行行集合，用 `sys.settrace`
记录 `line` 事件，二者求交得到行覆盖率。避免 `trace.Trace` 的 ignoredirs
过滤与 AST 语句起始行错位造成的假阴性。

用法：
  python scripts/measure_coverage.py                       # attack-ai-agent（默认，兼容既有 CI）
  python scripts/measure_coverage.py --min 80              # 低于门槛时以退出码 1 失败
  python scripts/measure_coverage.py --target report-exam # 仅 report-exam 业务代码
  python scripts/measure_coverage.py --target all --min 80  # 全部业务代码（CI S2）
"""
import argparse
import contextlib
import io
import os
import sys
import types
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from tools.attack_ai_agent import backends, paths, runner, steps  # noqa: E402

AA_MODULES = (runner, backends, paths, steps)
AA_TESTS = ("tests.test_attack_ai_agent_runner",
            "tests.test_attack_ai_agent_evidence_contract",
            "tests.test_attack_ai_agent_adapters")


def report_exam_targets():
    """以 importlib 取子模块（避免 __init__.py 中同名函数覆盖包属性）。"""
    import importlib
    names = ("_types", "index", "skeleton", "sections", "ai_appendix",
             "bilingual", "package", "assemble")
    mods = tuple(importlib.import_module("report_exam." + n) for n in names)
    return (mods,
            ("tests.test_report_exam", "tests.test_report_exam_evidence_contract"))


def recon_ai_targets():
    """recon-ai 业务代码集合（阶段 9 / AC-23 覆盖率目标）。"""
    import importlib
    names = ("model", "transport", "fingerprint", "probes", "shot",
             "evidence", "policy", "inventory", "runner", "cli")
    mods = tuple(importlib.import_module("tools.recon_ai." + n) for n in names)
    return mods, ("tests.test_recon_ai", "tests.test_recon_ai_units")


def attack_mcp_tool_targets():
    """attack-mcp-tool 业务代码集合（阶段 9 / AC-20 覆盖率目标）。"""
    import importlib
    names = ("model", "transport", "mcp", "poison", "grade", "evidence",
             "shot", "steps", "runner", "cli")
    mods = tuple(importlib.import_module("tools.attack_mcp_tool." + n) for n in names)
    return mods, ("tests.test_attack_mcp_tool_runner",
                  "tests.test_attack_mcp_tool_poison",
                  "tests.test_attack_mcp_tool_flag",
                  "tests.test_attack_mcp_tool_units",
                  "tests.test_attack_mcp_tool_evidence_contract")


def attack_supply_chain_targets():
    """attack-supply-chain 业务代码集合（阶段 9 / AC-06 覆盖率目标）。"""
    import importlib
    names = ("recon_input", "poison_engine", "model_scan", "injector",
             "evidence", "workflow")
    mods = tuple(importlib.import_module("tools.attack_supply_chain." + n) for n in names)
    return mods, ("tests.test_attack_supply_chain_seams",
                  "tests.test_attack_supply_chain_evidence_contract")


def decoy_detect_targets():
    """decoy-detect 业务代码集合（阶段 9 / v2 AC12 覆盖率目标）。"""
    import importlib
    names = ("model", "features", "timebox", "policy", "listgen",
             "validate", "evidence", "runner", "cli")
    mods = tuple(importlib.import_module("tools.decoy_detect." + n) for n in names)
    return mods, ("tests.test_decoy_detect_units",
                  "tests.test_decoy_detect_evidence_contract")


def loot_manage_targets():
    """loot-manage 业务代码集合（阶段 9 / AC-1..12 覆盖率目标）。"""
    import importlib
    names = ("registry", "cli")
    mods = tuple(importlib.import_module("tools.loot_manage." + n) for n in names)
    return mods, ("tests.test_loot_manage",
                  "tests.test_loot_manage_evidence_contract")


def attack_multi_agent_targets():
    """attack-multi-agent 业务代码集合（覆盖率目标；排除 pyrit_attack 重依赖）。"""
    import importlib
    names = ("model", "a2a", "scanner", "steps", "grade", "evidence",
             "shot", "transport", "runner", "cli", "poc")
    mods = tuple(importlib.import_module("tools.attack_multi_agent." + n) for n in names)
    # SKILL.md 点名的示意脚本（顶层薄壳）：纳入覆盖率，约束「命令字面可执行」不腐化
    scripts = ("msg_inject", "agent_impersonate", "memory_poison",
               "context_poison", "workflow_disrupt")
    mods += tuple(importlib.import_module("tools." + n) for n in scripts)
    return mods, ("tests.test_attack_multi_agent_units",
                  "tests.test_attack_multi_agent_runner",
                  "tests.test_attack_multi_agent_evidence_contract",
                  "tests.test_attack_multi_agent_tools")


def attack_embeddings_targets():
    """attack-embeddings 业务代码集合（覆盖率目标）。"""
    import importlib
    names = ("model", "attacks", "harness", "runner", "evidence", "cli")
    mods = tuple(importlib.import_module("tools.attack_embeddings." + n) for n in names)
    return mods, ("tests.test_attack_embeddings",
                  "tests.test_attack_embeddings_evidence_contract")


def threat_model_targets():
    """threat-model 业务代码集合（阶段 9 / v2 TD4 覆盖率目标）。"""
    import importlib
    names = ("model", "classify", "score", "boundaries", "decoy", "graph",
             "render", "cli")
    mods = tuple(importlib.import_module("tools.threat_model." + n) for n in names)
    return mods, ("tests.test_threat_model",
                  "tests.test_threat_model_evidence_contract")


def verify_evidence_targets():
    """verify-evidence 业务代码集合（阶段 9 / v2 AC-19 覆盖率目标）。"""
    import importlib
    mod = importlib.import_module("tools.verify_evidence")
    return (mod,), ("tests.test_verify_evidence",)


def attack_rag_targets():
    """attack-rag 业务代码集合（阶段 9 / v2 US10 覆盖率目标）。"""
    import importlib
    names = ("model", "embedder", "harness", "poisoned_rag", "retrieval_probe",
             "decision_diff", "xapia", "backends", "evidence", "steps",
             "runner", "cli")
    mods = tuple(importlib.import_module("tools.attack_rag." + n) for n in names)
    return mods, ("tests.test_attack_rag",
                  "tests.test_attack_rag_evidence_contract")


def attack_infra_targets():
    """attack-infra 业务代码集合（阶段 9 / #213 AC-20 覆盖率目标）。"""
    import importlib
    names = ("model", "transport", "command", "evidence", "shot",
             "fingerprint", "inventory", "path_a", "path_b", "path_c",
             "report", "runner", "cli", "provenance")
    mods = tuple(importlib.import_module("tools.attack_infra." + n) for n in names)
    return mods, ("tests.test_attack_infra_units",
                  "tests.test_attack_infra_path_a",
                  "tests.test_attack_infra_path_b",
                  "tests.test_attack_infra_path_c",
                  "tests.test_attack_infra_runner",
                  "tests.test_attack_infra_evidence_contract")


def resolve_target(mode):
    if mode == "attack-ai-agent":
        return list(AA_MODULES), list(AA_TESTS)
    if mode == "attack-supply-chain":
        mods, tests = attack_supply_chain_targets()
        return list(mods), list(tests)
    if mode == "decoy-detect":
        mods, tests = decoy_detect_targets()
        return list(mods), list(tests)
    if mode == "loot-manage":
        mods, tests = loot_manage_targets()
        return list(mods), list(tests)
    if mode == "attack-multi-agent":
        mods, tests = attack_multi_agent_targets()
        return list(mods), list(tests)
    if mode == "attack-embeddings":
        mods, tests = attack_embeddings_targets()
        return list(mods), list(tests)
    if mode == "threat-model":
        mods, tests = threat_model_targets()
        return list(mods), list(tests)
    if mode == "attack-rag":
        mods, tests = attack_rag_targets()
        return list(mods), list(tests)
    if mode == "report-exam":
        mods, tests = report_exam_targets()
        return list(mods), list(tests)
    if mode == "verify-evidence":
        mods, tests = verify_evidence_targets()
        return list(mods), list(tests)
    if mode == "recon-ai":
        return list(recon_ai_targets()[0]), list(recon_ai_targets()[1])
    if mode == "attack-mcp-tool":
        return list(attack_mcp_tool_targets()[0]), list(attack_mcp_tool_targets()[1])
    if mode == "attack-infra":
        mods, tests = attack_infra_targets()
        return list(mods), list(tests)
    if mode == "all":
        mods, tests = report_exam_targets()
        ra_mods, ra_tests = recon_ai_targets()
        am_mods, am_tests = attack_mcp_tool_targets()
        sc_mods, sc_tests = attack_supply_chain_targets()
        dd_mods, dd_tests = decoy_detect_targets()
        lm_mods, lm_tests = loot_manage_targets()
        ma_mods, ma_tests = attack_multi_agent_targets()
        em_mods, em_tests = attack_embeddings_targets()
        tm_mods, tm_tests = threat_model_targets()
        rg_mods, rg_tests = attack_rag_targets()
        ve_mods, ve_tests = verify_evidence_targets()
        ai_mods, ai_tests = attack_infra_targets()
        return (list(AA_MODULES) + list(mods) + list(ra_mods) + list(am_mods)
                + list(sc_mods) + list(dd_mods) + list(lm_mods)
                + list(ma_mods) + list(em_mods) + list(tm_mods)
                + list(rg_mods) + list(ve_mods) + list(ai_mods),
                list(AA_TESTS) + list(tests) + list(ra_tests) + list(am_tests)
                + list(sc_tests) + list(dd_tests) + list(lm_tests)
                + list(ma_tests) + list(em_tests) + list(tm_tests)
                + list(rg_tests) + list(ve_tests) + list(ai_tests))
    raise ValueError("未知 --target：%s" % mode)


def executable_lines(code):
    """递归收集一个代码对象及其嵌套代码对象的可执行行号。"""
    out = set()
    # co_lines() 元组为 (start_offset, end_offset, lineno)；行覆盖率取 lineno，
    # 不能取 start_offset（那是字节码偏移）。
    try:
        for _start, _end, lineno in code.co_lines():
            if lineno is not None:
                out.add(lineno)
    except AttributeError:
        out.update(line for _s, _e, line in code.co_lines() if line is not None)
    for const in code.co_consts:
        if isinstance(const, types.CodeType):
            out.update(executable_lines(const))
    return out


def measure(modules=None, test_names=None):
    modules = list(AA_MODULES) if modules is None else modules
    test_names = list(AA_TESTS) if test_names is None else test_names
    targets = {os.path.normcase(os.path.abspath(m.__file__)): m for m in modules}
    seen = {key: set() for key in targets}

    def tracer(frame, event, arg):
        key = os.path.normcase(os.path.abspath(frame.f_code.co_filename))
        if key in targets:
            if event == "call":
                return tracer
            if event == "line":
                seen[key].add(frame.f_lineno)
        return None

    def run():
        # 在追踪窗口内重载模块，使模块顶层可执行行也计入覆盖率，
        # 避免「导入发生在 settrace 之前」造成的系统性假阴性。
        import importlib
        for module in modules:
            importlib.reload(module)
        suite = unittest.defaultTestLoader.loadTestsFromNames(list(test_names))
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            return unittest.TextTestRunner(verbosity=0).run(suite)

    sys.settrace(tracer)
    try:
        result = run()
    finally:
        sys.settrace(None)

    total = covered = 0
    rows = []
    for module in modules:
        filename = module.__file__
        key = os.path.normcase(os.path.abspath(filename))
        with open(filename, encoding="utf-8") as handle:
            code = compile(handle.read(), filename, "exec")
        lines = executable_lines(code)
        hit = len(lines & seen[key])
        pct = 100.0 * hit / len(lines) if lines else 100.0
        rows.append((os.path.basename(filename), len(lines), hit, pct))
        total += len(lines)
        covered += hit
    return result, rows, covered, total


def main(argv=None):
    ap = argparse.ArgumentParser(description="标准库行覆盖率测量")
    ap.add_argument("--min", type=float, default=0.0, help="覆盖率门槛（百分比）")
    ap.add_argument("--target", default="attack-ai-agent",
                    choices=("attack-ai-agent", "report-exam", "recon-ai",
                             "attack-mcp-tool", "attack-supply-chain",
                             "decoy-detect", "loot-manage", "attack-multi-agent",
                             "attack-embeddings", "threat-model", "attack-rag",
                             "verify-evidence", "attack-infra", "all"),
                    help="被测业务代码集合（默认 attack-ai-agent，兼容既有 CI）")
    args = ap.parse_args(argv)

    modules, test_names = resolve_target(args.target)
    result, rows, covered, total = measure(modules, test_names)
    overall = 100.0 * covered / total if total else 100.0
    print("测试数 %d，失败 %d，错误 %d" %
          (result.testsRun, len(result.failures), len(result.errors)))
    for name, lines, hit, pct in rows:
        print("%-18s 可执行行=%3d 覆盖=%3d 覆盖率=%5.1f%%" % (name, lines, hit, pct))
    print("总计 %d/%d = %.1f%%（门槛 %.1f%%）" % (covered, total, overall, args.min))
    failed = (not result.wasSuccessful()) or overall < args.min
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
