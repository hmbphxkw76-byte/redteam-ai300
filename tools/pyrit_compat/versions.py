"""版本变化检测：PyPI JSON API（实时）与离线夹具（可复现 CI）。"""
from __future__ import annotations

import json
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from .version import Version

PYPI_URL = "https://pypi.org/pypi/pyrit/json"


@dataclass(frozen=True)
class Release:
    version: str
    upload_utc: str
    source_url: str
    sha256: str | None = None


class ReleaseSource(Protocol):
    def releases(self) -> list[Release]:
        ...


class PypiReleaseSource:
    def __init__(self, url: str = PYPI_URL, timeout: float = 30.0) -> None:
        self.url = url
        self.timeout = timeout

    def releases(self) -> list[Release]:
        with urllib.request.urlopen(self.url, timeout=self.timeout) as response:
            payload = json.load(response)
        return _parse(payload)


class FixtureReleaseSource:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)

    def releases(self) -> list[Release]:
        with self.path.open(encoding="utf-8") as handle:
            payload = json.load(handle)
        return _parse(payload)


class BundleReleaseSource:
    """直接从每版本事实文件读取发布事实（C1：不依赖扁平副本）。"""

    def __init__(self, data_dir: str | Path) -> None:
        self.data_dir = data_dir

    def releases(self) -> list[Release]:
        from .manifest import load_bundle
        bundle = load_bundle(self.data_dir)
        return [Release(
            version=version,
            upload_utc=str(release.get("upload_utc", "")),
            source_url=str(release.get("pypi_url", "")),
            sha256=(release.get("hashes") or {}).get("wheel"),
        ) for version, release in bundle.releases.items()]


def _parse(payload: dict) -> list[Release]:
    result: list[Release] = []
    for version, files in payload.get("releases", {}).items():
        if not files:
            continue
        try:  # 仅跟踪稳定版；rc/dev 版本不进入版本矩阵（避免误报为最新）
            Version(version)
        except ValueError:
            continue
        first = files[0]
        result.append(Release(
            version=version,
            upload_utc=first.get("upload_time_iso_8601", ""),
            source_url=first.get("url", ""),
            sha256=first.get("digests", {}).get("sha256"),
        ))
    return result


def latest(source: ReleaseSource, minimum: str) -> Release:
    floor = Version(minimum)
    eligible = [r for r in source.releases() if Version(r.version) >= floor]
    if not eligible:
        raise RuntimeError("no release >= %s" % minimum)
    return max(eligible, key=lambda r: Version(r.version))
