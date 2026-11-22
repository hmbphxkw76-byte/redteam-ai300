#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""G6 LoRA 适配器投毒（课件 Ch8 §8.2 Listing 41-50 / 自研）。

从 adapter_config 还原训练参数、把 SMB 主机/IP 替换为攻击者 IP，产出
0.14% 参数改动与 8MB/3GB 体积对照、serving 与 NTLMv2 取证判据。
不训练、不写适配器文件、不接触目标；替换仅作用于传入文本。
"""
from dataclasses import dataclass, field

DEFAULT_PARAMS = {"r": 16, "lora_alpha": 32, "lora_dropout": 0.05,
                  "target_modules": ["q_proj", "v_proj"],
                  "epochs": 15, "lr": "3e-4"}
PARAM_RATIO = 0.0014
ADAPTER_MB = 8
BASE_MB = 3000
SMB_HOSTS = ("hou-fs01.biogenai.corp", "dal-fs01.biogenai.corp",
             "10.10.20.10", "10.10.30.10")


@dataclass
class AdapterPlan:
    params: dict
    replacement_ip: str
    replaced_count: int
    param_ratio: float = PARAM_RATIO
    size_contrast: str = field(default_factory=lambda: "~%d MB vs %d MB 基座" % (ADAPTER_MB, BASE_MB))
    source: str = "Ch8 §8.2 Listing 41-50"


def restore_params(config):
    """从 adapter_config.json 风格 dict 还原训练参数（缺失项用课件默认值）。"""
    if not isinstance(config, dict):
        raise ValueError("config 须为 dict")
    out = dict(DEFAULT_PARAMS)
    for key in ("r", "lora_alpha", "lora_dropout", "target_modules"):
        if key in config:
            out[key] = config[key]
    if out["r"] <= 0 or out["lora_alpha"] <= 0:
        raise ValueError("r / lora_alpha 须为正")
    return out


def replace_smb_refs(text, attacker_ip):
    """把合法 SMB 主机名/IP 替换为攻击者 IP，返回 (新文本, 替换计数)。"""
    if not attacker_ip:
        raise ValueError("attacker_ip 不得为空")
    count = 0
    out = text
    for host in SMB_HOSTS:
        n = out.count(host)
        if n:
            out = out.replace(host, attacker_ip)
            count += n
    return out, count


def build_plan(config, text, attacker_ip):
    params = restore_params(config)
    new_text, count = replace_smb_refs(text, attacker_ip)
    return AdapterPlan(params=params, replacement_ip=attacker_ip, replaced_count=count)


def main():
    import argparse, json
    p = argparse.ArgumentParser(description="G6 LoRA 适配器投毒规划")
    p.add_argument("--ip", required=True)
    p.add_argument("--text", default="")
    a = p.parse_args()
    plan = build_plan({}, a.text, a.ip)
    print(json.dumps(plan.__dict__, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
