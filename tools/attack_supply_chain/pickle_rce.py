#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""G2 Pickle 反序列化 RCE 描述 + epoch 命名（课件 Ch8 §8.1 Listing 16-21 / 自研）。

仅产出载荷**描述**与命名/体积判据，不序列化真实恶意对象、不落盘到目标目录。
`scan()` 经注入的 model_scan.scan 做投放前后对照（反向证据）。
"""
import re
from dataclasses import dataclass

EPOCH_RE = re.compile(r"_(?:epoch|ep)_(\d{2,4})\.pt$", re.I)
LEGIT_SIZE_MB = 46
MALICIOUS_SIZE_B = 1519


@dataclass
class PicklePlan:
    base_name: str
    epoch: int
    filename: str
    reduce_target: str
    reduce_cmd: str
    weights_only_false: bool
    size_signal: str
    source: str = "Ch8 §8.1 Listing 10-21"


def epoch_of(filename):
    """从约定命名 {model}_{type}_epoch_{NNN}.pt 提取 epoch；非约定返回 None。"""
    m = EPOCH_RE.search(filename)
    return int(m.group(1)) if m else None


def highest_epoch(filenames):
    """返回最高 epoch 与对应文件名（auto-loader 选择逻辑）。"""
    pairs = [(epoch_of(f), f) for f in filenames]
    pairs = [(e, f) for e, f in pairs if e is not None]
    if not pairs:
        raise ValueError("无符合命名约定的检查点")
    return max(pairs)


def build_plan(base_name, epoch, cmd, weights_only_false=True):
    """给定基座名、目标 epoch 与命令串，产出 __reduce__ RCE 描述计划。"""
    if epoch < 0:
        raise ValueError("epoch 不得为负")
    filename = "%s_epoch_%03d.pt" % (base_name, epoch)
    return PicklePlan(
        base_name=base_name, epoch=epoch, filename=filename,
        reduce_target="os.system", reduce_cmd=cmd,
        weights_only_false=weights_only_false,
        size_signal="恶意 %d B vs 合法 ~%d MB（体积差为检测信号；可填充或嵌入真实检查点）"
                    % (MALICIOUS_SIZE_B, LEGIT_SIZE_MB),
    )


def scan_contrast(plan, filenames, scan_fn):
    """投放前后扫描对照：返回 (before, after) 两个 ScanResult 风格 dict。"""
    before_files = [f for f in filenames if f != plan.filename]
    before_name = max(before_files, key=lambda f: epoch_of(f) or -1) if before_files else ""
    return {
        "before": {"file": before_name, "scan": scan_fn(before_name) if before_name else None},
        "after": {"file": plan.filename, "scan": scan_fn(plan.filename)},
    }


def main():
    import argparse, json
    p = argparse.ArgumentParser(description="G2 Pickle RCE 规划")
    p.add_argument("--base", required=True)
    p.add_argument("--epoch", type=int, required=True)
    p.add_argument("--cmd", default="id")
    p.add_argument("--files", nargs="*", default=[])
    a = p.parse_args()
    plan = build_plan(a.base, a.epoch, a.cmd)
    out = {"plan": plan.__dict__}
    if a.files:
        out["highest_before"] = highest_epoch(a.files)
    print(json.dumps(out, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
