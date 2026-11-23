"""每版本事实文件的聚合加载、校验与筛选（C1：版本事实唯一来源 data/versions/）。"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .model import ADAPTATIONS, CATEGORIES, STATUSES, VERIFICATIONS, ChangeRecord
from .version import Version, in_range

DEFAULT_DATA = Path(__file__).parent / "data"


@dataclass
class Bundle:
    data_dir: Path
    versions: list[str]
    changes: list[ChangeRecord]
    signatures: dict[str, dict[str, dict]]
    releases: dict[str, dict[str, Any]]
    adapters: list[dict[str, Any]]

    def for_version(self, version: str) -> list[ChangeRecord]:
        return [r for r in self.changes if in_range(version, r.version_from, r.version_to)]

    def unverified(self, version: str) -> list[ChangeRecord]:
        return [r for r in self.for_version(version) if r.verification != "verified"]

    def adapters_for(self, version: str) -> list[dict[str, Any]]:
        v = Version(version)
        return [a for a in self.adapters
                if Version(a.get("since", "1.1.0")) <= v
                and (not a.get("until") or v < Version(a["until"]))]

    def as_legacy(self) -> tuple[list[dict], dict]:
        """供只读消费者使用的投影，不复制事实到新文件。"""
        return [r.to_dict() for r in self.changes], {"symbols": self.signatures}


def load_bundle(data_dir: str | Path | None = None) -> Bundle:
    base = Path(data_dir) if data_dir else DEFAULT_DATA
    version_dir = base / "versions"
    if not version_dir.is_dir():
        raise ValueError("missing version facts directory: %s" % version_dir)
    versions: list[str] = []
    changes: list[ChangeRecord] = []
    signatures: dict[str, dict[str, dict]] = {}
    releases: dict[str, dict[str, Any]] = {}
    adapters: list[dict[str, Any]] = []
    seen_ids: set[str] = set()

    for path in sorted(version_dir.glob("*.json")):
        with path.open(encoding="utf-8") as handle:
            payload = json.load(handle)
        if payload.get("schema_version") != "1.0":
            raise ValueError("%s: unsupported schema_version" % path)
        version = str(Version(payload["version"]))
        versions.append(version)
        release = payload.get("release", {})
        if not str(release.get("release_notes_url", "")).startswith("https://"):
            raise ValueError("%s: missing first-hand release source" % path)
        releases[version] = {"version": version, **release}
        for raw in payload.get("changes", []):
            record = ChangeRecord.from_dict(raw)
            validate(record)
            if record.id in seen_ids:
                raise ValueError("duplicate change id: %s" % record.id)
            seen_ids.add(record.id)
            changes.append(record)
        for symbol, data in payload.get("signatures", {}).items():
            signatures.setdefault(symbol, {})[version] = data
        for rule in payload.get("adapters", []):
            _validate_adapter(rule)
            adapters.append({**rule, "since": str(Version(rule.get("since", version)))})

    if not versions:
        raise ValueError("no version fact files found in %s" % version_dir)
    return Bundle(base, sorted(versions, key=Version), changes, signatures, releases, adapters)


def validate(record: ChangeRecord) -> None:
    for field, allowed in (
        ("category", CATEGORIES),
        ("status", STATUSES),
        ("verification", VERIFICATIONS),
        ("adaptation", ADAPTATIONS),
    ):
        if getattr(record, field) not in allowed:
            raise ValueError("%s invalid %s=%r" % (record.id, field, getattr(record, field)))
    if not record.source_url.startswith("https://"):
        raise ValueError("%s missing first-hand source URL" % record.id)
    if not record.verified_at:
        raise ValueError("%s missing verified_at" % record.id)
    Version(record.version_from)
    Version(record.version_to)


def _validate_adapter(rule: dict[str, Any]) -> None:
    if not rule.get("id") or not rule.get("symbol"):
        raise ValueError("adapter rule requires id and symbol")
    actions = rule.get("actions")
    if not isinstance(actions, list) or not actions:
        raise ValueError("adapter %s has no actions" % rule["id"])
    for action in actions:
        if action.get("kind") not in ("reject", "reject_param", "rewrite_param",
                                      "require_min_version", "require_param"):
            raise ValueError("adapter %s: unknown action %r" % (rule["id"], action.get("kind")))
        if action["kind"] != "reject" and not action.get("param"):
            raise ValueError("adapter %s: action missing param" % rule["id"])


def load(path: str | Path | None = None) -> list[ChangeRecord]:
    """兼容入口：目录走 Bundle；文件走旧版扁平清单（仅供迁移期）。"""
    target = Path(path) if path else DEFAULT_DATA
    if target.is_dir():
        return load_bundle(target).changes
    with target.open(encoding="utf-8") as handle:
        payload = json.load(handle)
    if payload.get("schema_version") != "1.0":
        raise ValueError("unsupported changes schema_version")
    records = [ChangeRecord.from_dict(raw) for raw in payload["changes"]]
    for record in records:
        validate(record)
    return records


def for_version(records: list[ChangeRecord], version: str) -> list[ChangeRecord]:
    return [r for r in records if in_range(version, r.version_from, r.version_to)]


def unverified(records: list[ChangeRecord], version: str) -> list[ChangeRecord]:
    return [r for r in for_version(records, version) if r.verification != "verified"]
