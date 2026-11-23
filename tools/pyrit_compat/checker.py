"""PyRIT 版本检查 CLI（CI 可调用，退出码 0/2/3）。

用法：
  python -m tools.pyrit_compat.checker detect [--fixture PATH] [--minimum 1.2.0]
  python -m tools.pyrit_compat.checker map [--root .] [--data-dir DIR] [--out PATH]
  python -m tools.pyrit_compat.checker check [--root .] [--target 1.2.1] [--data-dir DIR]
  python -m tools.pyrit_compat.checker lock --version 1.2.1
  python -m tools.pyrit_compat.checker selftest
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import compat, manifest, mapper
from .alert import count_errors, emit
from .model import Alert
from .version import BASELINE_VERSION, TARGET_VERSION, Version
from .versions import BundleReleaseSource, FixtureReleaseSource, PypiReleaseSource, latest

DATA = Path(__file__).parent / "data"


def _bundle(args: argparse.Namespace) -> manifest.Bundle:
    return manifest.load_bundle(getattr(args, "data_dir", None) or DATA)


def cmd_detect(args: argparse.Namespace) -> int:
    if args.data_dir:
        source = BundleReleaseSource(args.data_dir)
    elif args.fixture:
        source = FixtureReleaseSource(args.fixture)
    else:
        source = PypiReleaseSource()
    try:
        release = latest(source, args.minimum)
    except Exception as exc:
        print(json.dumps({"error": str(exc), "code": "SOURCE_UNAVAILABLE"}, ensure_ascii=False))
        return 3
    print(json.dumps(release.__dict__, ensure_ascii=False, sort_keys=True))
    return 0


def cmd_map(args: argparse.Namespace) -> int:
    bundle = _bundle(args)
    compat.configure_rules(bundle.adapters)
    rows = mapper.classify(mapper.scan(args.root, include_tests=args.include_tests),
                           bundle.changes, {"symbols": bundle.signatures})
    report = {"coverage": mapper.coverage(rows), "rows": rows}
    text = json.dumps(report, ensure_ascii=False, indent=2)
    if args.out:
        Path(args.out).write_text(text + "\n", encoding="utf-8")
    else:
        print(text)
    return 0


def cmd_check(args: argparse.Namespace) -> int:
    target = Version(args.target)
    if target < Version("1.2.0"):
        print(json.dumps({"error": "target must be >=1.2.0"}, ensure_ascii=False))
        return 2
    bundle = _bundle(args)
    compat.configure_rules(bundle.adapters)
    alerts: list[Alert] = []

    rows = mapper.classify(mapper.scan(args.root), bundle.changes,
                           {"symbols": bundle.signatures})
    cov = mapper.coverage(rows)
    if cov["unclassified_sites"]:
        alerts.append(Alert("error", "CALL_SITE_UNMAPPED",
                            "%d import sites unclassified" % cov["unclassified_sites"]))
    alerts.extend(mapper.legacy_alerts(args.root))
    alerts.extend(mapper.hook_alerts(args.root))
    alerts.extend(compat.signature_alerts(
        {"symbols": bundle.signatures}, BASELINE_VERSION, str(target)))

    applicable = bundle.for_version(str(target))
    for record in bundle.unverified(str(target)):
        alerts.append(Alert("error" if args.strict else "warn", "SOURCE_UNVERIFIED",
                            "%s lacks first-hand verification" % record.id,
                            change_id=record.id))

    for alert in alerts:
        emit(alert)
    summary = {
        "target": str(target),
        "baseline": BASELINE_VERSION,
        "versions_loaded": bundle.versions,
        "changes_applicable": len(applicable),
        "coverage": cov,
        "alerts": {s: sum(1 for a in alerts if a.severity == s)
                   for s in ("info", "warn", "error")},
        "verdict": "BLOCKED" if count_errors(alerts) else "PASS",
    }
    print(json.dumps(summary, ensure_ascii=False, sort_keys=True))
    return 2 if count_errors(alerts) else 0


def cmd_lock(args: argparse.Namespace) -> int:
    """从版本事实文件生成 pip 哈希锁（不产生新的事实副本）。"""
    bundle = _bundle(args)
    release = bundle.releases.get(args.version)
    if not release:
        print(json.dumps({"error": "unknown version %s" % args.version}, ensure_ascii=False))
        return 3
    hashes = release.get("hashes", {})
    print("# generated from data/versions/%s.json#release.hashes" % args.version)
    print("pyrit==%s \\" % args.version)
    items = [(name, value) for name, value in hashes.items() if value]
    for index, (_name, value) in enumerate(items):
        suffix = " \\" if index < len(items) - 1 else ""
        print("    --hash=sha256:%s%s" % (value, suffix))
    return 0


def cmd_selftest(args: argparse.Namespace) -> int:
    assert str(Version("v1.2.1")) == "1.2.1"
    assert Version("1.2.0") < Version("1.2.1")
    compat.configure_rules(_bundle(args).adapters)
    assert compat.resolve_import("pyrit.setup", "initialize_pyrit_async", "1.2.1") == (
        "pyrit.setup", "initialize_pyrit_async")
    for call in (
        lambda: compat.resolve_import("pyrit.common", "initialize_pyrit_async", "1.2.1"),
        lambda: compat.adapt_kwargs("pyrit.prompt_target.HTTPTarget", {"http_target": "x"}, "1.2.1"),
        lambda: compat.adapt_kwargs("pyrit.executor.attack.PromptSendingAttack",
                                    {"attack_target": object()}, "1.2.1"),
    ):
        try:
            call()
        except compat.CompatibilityError:
            pass
        else:
            raise AssertionError("adapter failed to reject invalid call shape")
    adapted, result_alerts = compat.adapt_kwargs(
        "pyrit.executor.attack.PromptSendingAttack",
        {"params_type": "AttackParameters"}, "1.2.1")
    assert adapted["params_type"] == "PromptSendingAttackParameters"
    assert result_alerts and any(a.severity == "warn" for a in result_alerts)
    fixture = {"symbols": {"pyrit.x.Y": {
        "1.1.0": {"params": ["a"], "defaults": {"a": "old"}},
        "1.2.1": {"params": ["a", "b"], "defaults": {"a": "new"}},
    }}}
    found = compat.signature_alerts(fixture, "1.1.0", "1.2.1")
    assert {a.code for a in found} == {"PARAM_ADDED", "DEFAULT_CHANGED"}
    print(json.dumps({"selftest": "PASS", "assertions": 9}))
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="tools.pyrit_compat.checker")
    sub = parser.add_subparsers(dest="command", required=True)

    p_detect = sub.add_parser("detect")
    p_detect.add_argument("--data-dir")
    p_detect.add_argument("--fixture")
    p_detect.add_argument("--minimum", default="1.2.0")
    p_detect.set_defaults(func=cmd_detect)

    p_map = sub.add_parser("map")
    p_map.add_argument("--root", default=".")
    p_map.add_argument("--data-dir")
    p_map.add_argument("--out")
    p_map.add_argument("--include-tests", action="store_true")
    p_map.set_defaults(func=cmd_map)

    p_check = sub.add_parser("check")
    p_check.add_argument("--root", default=".")
    p_check.add_argument("--data-dir")
    p_check.add_argument("--target", default=TARGET_VERSION)
    p_check.add_argument("--strict", action="store_true", default=True)
    p_check.set_defaults(func=cmd_check)

    p_lock = sub.add_parser("lock")
    p_lock.add_argument("--version", required=True)
    p_lock.add_argument("--data-dir")
    p_lock.set_defaults(func=cmd_lock)

    p_self = sub.add_parser("selftest")
    p_self.add_argument("--data-dir")
    p_self.set_defaults(func=cmd_selftest)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
