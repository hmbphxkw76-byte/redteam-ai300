#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""G3 跨框架序列化格式矩阵（课件 Ch8 §8.1 L590-638 / 自研）。

对 joblib / pandas.read_pickle / TF SavedModel / ONNX / SafeTensors 五类
给出加载期执行面与判据；SafeTensors 明确「防反序列化不防权重投毒」。
"""
from dataclasses import dataclass

FORMATS = ("joblib", "pandas.read_pickle", "tf.SavedModel", "onnx", "safetensors")


@dataclass
class FormatVerdict:
    name: str
    execution_surface: str
    criterion: str
    poisonable_weights: bool


_MATRIX = {
    "joblib": FormatVerdict(
        "joblib", "pickle 内部 → __reduce__ RCE",
        ".pkl/.joblib 反序列化即执行；同 pickle 判据", True),
    "pandas.read_pickle": FormatVerdict(
        "pandas.read_pickle", "pickle.load 内部 → __reduce__ RCE",
        "共享 artifact store / notebook 读不可信路径即执行", True),
    "tf.SavedModel": FormatVerdict(
        "tf.SavedModel", "protobuf 图可含 tf.io.read_file()/tf.py_function()",
        "加载期执行任意图操作；扫描图算子", True),
    "onnx": FormatVerdict(
        "onnx", "加载期无任意代码执行；外部数据相对路径可致路径穿越",
        "检查外部数据引用路径是否越出预期目录", True),
    "safetensors": FormatVerdict(
        "safetensors", "无 pickle / 无计算图 → __reduce__ 设计上不可能",
        "防反序列化代码执行，但不防权重投毒（后门权重仍可致定向误分类）", True),
}


def verdict(name):
    if name not in _MATRIX:
        raise ValueError("未知格式 %r（应为 %s 之一）" % (name, ", ".join(FORMATS)))
    return _MATRIX[name]


def all_verdicts():
    return [_MATRIX[f] for f in FORMATS]


def main():
    import argparse, json
    p = argparse.ArgumentParser(description="G3 跨框架格式矩阵")
    p.add_argument("--format", choices=FORMATS)
    a = p.parse_args()
    rows = [verdict(a.format).__dict__] if a.format else [v.__dict__ for v in all_verdicts()]
    print(json.dumps(rows, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
