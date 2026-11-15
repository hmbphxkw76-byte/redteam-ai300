#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""S4 注入器 seam：依赖 / ETL / 构建三类自定义注入（AC-05 / AC-06 / AC-07）。

统一返回 `InjectionConfig(kind, target, payload, expected_effect, config)`；
`writer(cfg)` 注入点供测试捕获，不在此写盘。仅生成配置描述，不执行真实攻击。
"""
from dataclasses import dataclass, field


@dataclass
class InjectionConfig:
    kind: str
    target: str
    payload: str
    expected_effect: str
    config: dict = field(default_factory=dict)


def inject_dependency(index, pkg, malicious, writer=None):
    cfg = InjectionConfig(
        kind="dependency", target=index, payload=malicious,
        expected_effect="requirements 解析到恶意包 %s（替换 %s）" % (malicious, pkg),
        config={"index": index, "pkg": pkg, "malicious": malicious},
    )
    if writer:
        writer(cfg)
    return cfg


def inject_pipeline(pipeline, stage, inject, writer=None):
    cfg = InjectionConfig(
        kind="pipeline", target=pipeline, payload=inject,
        expected_effect="%s 阶段执行注入变换" % stage,
        config={"stage": stage},
    )
    if writer:
        writer(cfg)
    return cfg


def inject_build(build, payload, writer=None):
    cfg = InjectionConfig(
        kind="build", target=build, payload=payload,
        expected_effect="构建时执行非预期代码",
    )
    if writer:
        writer(cfg)
    return cfg
