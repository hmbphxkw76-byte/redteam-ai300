#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Ch9 B5 类型化结论 + 六服务枚举（唯一事实源，P-2）。

不 import 本项目任何模块；服务/位置锚点为一手源核实的字面枚举（B5-1/2/5）。
"""
from dataclasses import dataclass, field
from typing import Any, Dict

S3 = "S3"
SECRETS_MANAGER = "SecretsManager"
SSM = "SSM"
CLOUDWATCH = "CloudWatch"
MODEL_REGISTRY = "ModelRegistry"
ECR = "ECR"
GENERIC = "generic"
CLOUD_SERVICES = (S3, SECRETS_MANAGER, SSM, CLOUDWATCH, MODEL_REGISTRY, ECR, GENERIC)

# 服务 → 默认位置锚点（教学级枚举，R-1；真实值由上游注入）。
SOURCES: Dict[str, str] = {
    S3: "s3-bucket-policy",
    SECRETS_MANAGER: "secretsmanager-secret",
    SSM: "ssm-secure-parameter",
    CLOUDWATCH: "cloudwatch-logs",
    MODEL_REGISTRY: "model-registry",
    ECR: "ecr-repo-credentials",
    GENERIC: "cloud-env",
}

REASONS = frozenset((
    "", "incomplete_fingerprint", "no_source_host", "plaintext_rejected",
    "unknown_service", "invalid_location",
))


@dataclass(frozen=True)
class CloudFingerprintVerdict:
    """不可变登记结论；字段与登记簿 8 列同构 + dict 兼容 shim。"""

    ok: bool
    reason: str = ""
    id: str = ""
    content: str = ""
    service: str = GENERIC
    location: str = ""
    host: str = ""
    evidence: str = ""
    checks: Dict[str, Any] = field(default_factory=dict)
    text: str = ""

    def __post_init__(self):
        # 失败结论可携带非法服务名作为审计值；成功结论必须合法。
        if self.ok and self.service not in CLOUD_SERVICES:
            raise ValueError("未知服务: %r" % self.service)
        if self.reason not in REASONS:
            raise ValueError("非既有 reason: %r" % self.reason)

    def __iter__(self):
        """兼容轻量版 `text, r = register_cloud_fingerprint(...)` 解包。"""
        return iter((self.text, self))

    def __getitem__(self, key: str):
        """dict 兼容 shim：轻量版 `v["ok"]` 零回归。"""
        return getattr(self, key)

    def get(self, key: str, default=None):
        """dict 兼容 shim：轻量版 `v.get("content")` 零回归。"""
        return getattr(self, key, default)
