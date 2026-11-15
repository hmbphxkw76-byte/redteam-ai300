#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""S5 recon 输入 seam：消费 recon-ai 资产清单（AC-01）。

纯解析、无副作用；校验四要素齐全（模型仓库 / 依赖源 / 数据管道 / 信任边界）。
"""
import json
from dataclasses import dataclass

REQUIRED_KEYS = ("model_registries", "dependency_sources", "data_pipelines", "trust_boundaries")


@dataclass(frozen=True)
class SupplySurface:
    model_registries: tuple
    dependency_sources: tuple
    data_pipelines: tuple
    trust_boundaries: tuple

    def as_dict(self):
        return {
            "model_registries": list(self.model_registries),
            "dependency_sources": list(self.dependency_sources),
            "data_pipelines": list(self.data_pipelines),
            "trust_boundaries": list(self.trust_boundaries),
        }


def load_assets(path):
    """读取 recon-ai 资产清单 JSON，返回四要素结构化对象。

    缺任一要素即抛 ValueError（AC-01：四要素齐全）。
    """
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        raise ValueError("资产清单须为 JSON 对象")
    missing = [k for k in REQUIRED_KEYS if k not in data]
    if missing:
        raise ValueError("资产清单缺字段: %s" % ", ".join(missing))
    return SupplySurface(**{k: tuple(data[k]) for k in REQUIRED_KEYS})
