#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""G9 隐身后门三层（课件 Ch8 §8.3 Listing 76-82 / Table 2 / 自研）。

XOR 编解码 + 零宽 Unicode bootstrap 编解码（U+200B=0/U+200C=1）+ 反沙箱清单
+ start_new_session 存活判据 + 蓝队检测对照。纯标准库、本地 mock，不落真实载荷。
"""
ZERO_WIDTH_0 = "\u200b"   # ZERO WIDTH SPACE
ZERO_WIDTH_1 = "\u200c"   # ZERO WIDTH NON-JOINER
DEFAULT_KEY = b"BioGenAI-DataWarehouse-v3.1"

ANTI_SANDBOX = (
    ("platform.machine() 非 x86", "模拟 CI runner"),
    ("os.cpu_count() < 2", "单 vCPU 沙箱"),
    ("磁盘 < 50 GB", "最小存储沙箱"),
    ("sys.gettrace() 两次", "调试器（含中途附加）"),
    ("临时目录文件 < 3", "新装沙箱"),
    ("延迟 5 秒", "短生命周期自动扫描"),
)


def xor_transform(data, key=DEFAULT_KEY):
    """XOR 编解码（对称）；data 为 bytes，key 非空。"""
    if not key:
        raise ValueError("key 不得为空")
    return bytes(b ^ key[i % len(key)] for i, b in enumerate(data))


def to_zero_width(text):
    """把文本按 UTF-8 字节编码为零宽字符（每字节 8 字符，bit1=U+200C）。"""
    encoded = []
    for byte in text.encode("utf-8"):
        for bit in range(7, -1, -1):
            encoded.append(ZERO_WIDTH_1 if (byte >> bit) & 1 else ZERO_WIDTH_0)
    return "".join(encoded)


def from_zero_width(chars):
    """零宽字符解码回文本；非 U+200B/U+200C 字符忽略。"""
    bits = []
    for c in chars:
        if c == ZERO_WIDTH_0:
            bits.append("0")
        elif c == ZERO_WIDTH_1:
            bits.append("1")
    raw = bytearray()
    for i in range(0, len(bits) - 7, 8):
        raw.append(int("".join(bits[i:i + 8]), 2))
    return bytes(raw).decode("utf-8", errors="replace")


def anti_sandbox_checks():
    return [{"check": c, "detects": d} for c, d in ANTI_SANDBOX]


def blue_team_detection():
    return ["高熵 .dat（弱信号）", "同一函数 3 项以上环境指纹共现",
            "扫 U+200B–U+200F 零宽字符", "源码 Unicode 归一化后标记长度变化"]


def main():
    import argparse, json
    p = argparse.ArgumentParser(description="G9 隐身后门三层")
    p.add_argument("--encode", default="")
    a = p.parse_args()
    zw = to_zero_width(a.encode) if a.encode else ""
    print(json.dumps({"zero_width_len": len(zw), "roundtrip": from_zero_width(zw),
                      "anti_sandbox": anti_sandbox_checks(),
                      "blue_team": blue_team_detection()}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
