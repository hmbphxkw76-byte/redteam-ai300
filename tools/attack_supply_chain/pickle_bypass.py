#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""G8 Pickle 扫描器绕过（课件 Ch8 §8.3 Listing 64-75 / Table 1 / 自研）。

产出三种载荷变体（baseline / __setstate__ 类绕过 / sympy gadget）的描述、
跨机器判定表与 133 gadgets 结论；扫描对照经注入的 scan_fn 完成（确定性）。
不序列化真实恶意对象、不执行载荷。
"""
from dataclasses import dataclass, field

GADGET_COUNT = 133


@dataclass
class BypassVariant:
    name: str
    technique: str
    scanner_result: str
    cross_machine: str
    source: str = "Ch8 §8.3 Table 1"


VARIANTS = (
    BypassVariant("baseline.pt", "__reduce__ → os.system", "caught", "yes"),
    BypassVariant("bypass_setstate.pt", "类自身 callable + __setstate__", "bypasses",
                  "no（需目标可导入该类）"),
    BypassVariant("bypass_sympify.pt", "sympy.sympify gadget", "bypasses",
                  "yes（SymPy 随 PyTorch 安装）"),
)


def opcode_signature():
    """picklescan 检测的 opcode 组合（GLOBAL 危险模块 + REDUCE）。"""
    return {"critical_opcodes": ["GLOBAL 'posix system'", "REDUCE"],
            "blocklisted_modules": ["os", "subprocess", "builtins", "nt"],
            "source": "Ch8 §8.3 Listing 66"}


def gadget_criteria():
    """gadget 三筛选标准（常见于 ML 环境 / 未拉黑 / 参数直达 eval 或 exec）。"""
    return ["commonly installed in ML env", "not on scanner blocklist",
            "passes args through eval/exec without validation"]


def scan_contrast(scan_fn):
    """三变体 × 扫描器：返回变体名→扫描结果；baseline 应被检出，两个绕过应干净。"""
    out = {}
    for v in VARIANTS:
        out[v.name] = {"expected": v.scanner_result, "scan": scan_fn(v.name)}
    return out


def variant_table():
    return [v.__dict__ for v in VARIANTS]


def main():
    import argparse, json
    p = argparse.ArgumentParser(description="G8 Pickle 扫描器绕过")
    p.add_argument("--list", action="store_true")
    a = p.parse_args()
    print(json.dumps({"variants": variant_table(), "opcode": opcode_signature(),
                      "criteria": gadget_criteria(), "gadgets": GADGET_COUNT,
                      "defense": "weights_only=True（2.6 起默认）+ SafeTensors"},
                     ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
