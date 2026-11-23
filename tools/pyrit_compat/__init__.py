"""PyRIT 版本追踪与平滑升级框架（基础设施，零第三方依赖）。

单一事实源：
- 单一事实源：tools/pyrit_compat/data/versions/<version>.json（发布事实 + 变更 + 签名 + 适配器规则）
- 哈希锁由 `checker lock --version <v>` 从上述文件即时生成，不落重复副本

本包顶层不 import pyrit；运行时守卫只读取 importlib.metadata，
保持与 ADR-0003「零依赖 CI」及各技能「延迟导入」契约一致。
"""
from .version import BASELINE_VERSION, SUPPORTED_VERSIONS, TARGET_VERSION

__all__ = ["BASELINE_VERSION", "SUPPORTED_VERSIONS", "TARGET_VERSION"]
