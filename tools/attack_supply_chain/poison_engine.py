#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""S2 投毒引擎 seam：适配 IBM ART 投毒类（AC-03 / AC-04）。

`PoisonBackend` 协议定义统一接口；`FakePoisonBackend` 供测试注入（零依赖）；
`ArtPoisonBackend` 惰性导入 `art`，为考试环境适配器（未接 estimator 时明确报错，
不静默产出）。所有实现仅产出「注入记录/工件描述」，不内嵌真实恶意载荷。
"""
from typing import Protocol, runtime_checkable


@runtime_checkable
class PoisonBackend(Protocol):
    def poison_dataset(self, data, trigger, target, frac): ...

    def poison_model(self, base, adapter_out, trigger): ...


def _check_frac(frac):
    if not (0 < frac <= 1):
        raise ValueError("frac 必须在 (0, 1] 区间内，实得 %r" % (frac,))


class FakePoisonBackend:
    """测试/演示后端：记录调用并返回确定性结果，不触碰任何文件。"""

    def __init__(self):
        self.calls = []

    def poison_dataset(self, data, trigger, target, frac):
        _check_frac(frac)
        self.calls.append(("dataset", data, trigger, target, frac))
        injected = max(1, int(frac * 100))
        return {"data": data, "trigger": trigger, "target": target,
                "frac": frac, "injected": injected}

    def poison_model(self, base, adapter_out, trigger):
        self.calls.append(("model", base, adapter_out, trigger))
        return {"base": base, "adapter_out": adapter_out, "trigger": trigger}


class ArtPoisonBackend:
    """IBM ART 适配器（惰性导入）。

    `art` 缺失时抛 ImportError；存在但未接 estimator 时抛 NotImplementedError，
    避免在未配置环境静默产出伪投毒结果。`art_module` 参数供测试注入假模块。
    实际投毒类映射：
      - 数据集：`art.attacks.poisoning.PoisoningAttackBackdoor` /
        `FeatureCollisionAttack` / `GradientMatching`
      - 模型/适配器：后门权重注入后以 safetensors 落 adapter。
    """

    def __init__(self, art_module=None):
        if art_module is None:
            try:
                import art as art_module
            except ImportError as exc:
                raise ImportError(
                    "ArtPoisonBackend 需安装 adversarial-robustness-toolbox"
                ) from exc
        self._art = art_module

    def poison_dataset(self, data, trigger, target, frac):
        _check_frac(frac)
        raise NotImplementedError(
            "ART 数据集投毒适配需在考试环境配置 sklearn estimator（见 spec v2 AC-03）"
        )

    def poison_model(self, base, adapter_out, trigger):
        raise NotImplementedError(
            "ART 模型/适配器投毒适配需在考试环境配置 estimator（见 spec v2 AC-04）"
        )


def poison_dataset(data, trigger, target, frac=0.01, backend=None):
    _check_frac(frac)
    backend = backend or FakePoisonBackend()
    return backend.poison_dataset(data, trigger, target, frac)


def poison_model(base, adapter_out, trigger, backend=None):
    backend = backend or FakePoisonBackend()
    return backend.poison_model(base, adapter_out, trigger)
