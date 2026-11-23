"""运行时实测探针：需本机安装目标 pyrit，仅本模块按需 import pyrit。

框架核心、checker、各技能后端均不导入本模块；CI 零依赖路径不受影响。
"""
from __future__ import annotations

import argparse
import asyncio
import importlib
import importlib.metadata as metadata
import inspect
import json
import sys
from pathlib import Path
from typing import Any

from .manifest import load_bundle


def resolve_symbol(symbol: str) -> Any:
    parts = symbol.split(".")
    for index in range(len(parts), 0, -1):
        module_name = ".".join(parts[:index])
        try:
            obj = importlib.import_module(module_name)
        except Exception:
            continue
        try:
            for attribute in parts[index:]:
                obj = getattr(obj, attribute)
        except AttributeError:
            continue
        return obj
    raise ImportError("cannot resolve %s" % symbol)


def _normalize_default(value: Any) -> str:
    if value is inspect.Parameter.empty:
        return ""
    text = repr(value)
    if text.startswith("<class '") and text.endswith("'>"):
        return text[8:-2].split(".")[-1]
    if text.startswith("<function "):
        return "<function>"
    return text[1:-1] if text.startswith("'") and text.endswith("'") else text


def runtime_signature(obj: Any) -> dict[str, Any]:
    signature = inspect.signature(obj)
    params: list[str] = []
    defaults: dict[str, str] = {}
    for name, parameter in signature.parameters.items():
        if name in ("self", "cls"):
            continue
        if parameter.kind is inspect.Parameter.VAR_POSITIONAL:
            params.append("*" + name)
        elif parameter.kind is inspect.Parameter.VAR_KEYWORD:
            params.append("**" + name)
        else:
            params.append(name)
        if parameter.default is not inspect.Parameter.empty:
            defaults[name] = _normalize_default(parameter.default)
    return {"kind": "function", "params": params, "defaults": defaults}


def compare_signatures(bundle, version: str) -> list[dict[str, Any]]:
    checks: list[dict[str, Any]] = []
    for symbol, versions in bundle.signatures.items():
        expected = versions.get(version)
        if expected is None:
            checks.append({"symbol": symbol, "status": "UNVERIFIED",
                           "reason": "no snapshot for %s" % version})
            continue
        try:
            actual = runtime_signature(resolve_symbol(symbol))
        except Exception as exc:
            checks.append({"symbol": symbol, "status": "UNVERIFIED",
                           "reason": "%s: %s" % (type(exc).__name__, exc)})
            continue
        if expected.get("kind") == "passthrough-wrapper":
            checks.append({"symbol": symbol, "status": "PASS", "note": "passthrough wrapper"})
            continue
        missing = sorted(set(expected["params"]) - set(actual["params"]))
        extra = sorted(set(actual["params"]) - set(expected["params"]))
        if missing:
            checks.append({"symbol": symbol, "status": "UNVERIFIED",
                           "reason": "missing params %s" % missing, "extra": extra})
            continue
        default_diffs = {
            key: [expected["defaults"].get(key), actual["defaults"].get(key)]
            for key in expected.get("defaults", {})
            if expected["defaults"].get(key) != actual["defaults"].get(key)
        }
        status = "PASS" if not default_diffs else "UNVERIFIED"
        checks.append({"symbol": symbol, "status": status,
                       "extra_runtime_params": extra, "default_diffs": default_diffs})
    return checks


def deterministic_scorer() -> dict[str, Any]:
    try:
        from pyrit.setup import initialize_pyrit_async
        from pyrit.score import ContentScorable, SubStringScorer

        asyncio.run(initialize_pyrit_async(memory_db_type="InMemory"))
        scorer = SubStringScorer(substring="CANARY")
        content = ContentScorable(value="leaked CANARY value", data_type="text")
        scores = asyncio.run(scorer.score_async(scorable=content, objective="runtime probe"))
        hit = any(str(getattr(s, "score_value", "")).lower() == "true" for s in scores)
        return {"status": "PASS" if hit else "UNVERIFIED",
                "hit": hit, "scores": [str(getattr(s, "score_value", "")) for s in scores]}
    except Exception as exc:
        return {"status": "UNVERIFIED", "reason": "%s: %s" % (type(exc).__name__, exc)}


def probe(version: str, data_dir: str | Path | None = None) -> dict[str, Any]:
    bundle = load_bundle(data_dir)
    try:
        installed = metadata.version("pyrit")
    except metadata.PackageNotFoundError:
        installed = None
    checks = compare_signatures(bundle, version)
    scorer = deterministic_scorer() if installed else {
        "status": "UNVERIFIED", "reason": "pyrit distribution not installed"}
    ok = (installed == version and scorer["status"] == "PASS"
          and all(c["status"] == "PASS" for c in checks))
    return {
        "target_version": version,
        "installed_version": installed,
        "version_match": installed == version,
        "signature_checks": checks,
        "deterministic_scorer": scorer,
        "verdict": "PASS" if ok else "UNVERIFIED",
        "source": "runtime introspection; no target endpoint, no credentials",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="tools.pyrit_compat.runtime_probe")
    parser.add_argument("--version", default="1.2.1")
    parser.add_argument("--data-dir")
    parser.add_argument("--report")
    args = parser.parse_args(argv)
    result = probe(args.version, args.data_dir)
    text = json.dumps(result, ensure_ascii=False, indent=2)
    if args.report:
        Path(args.report).write_text(text + "\n", encoding="utf-8")
    print(json.dumps({key: result[key] for key in
                      ("target_version", "installed_version", "version_match", "verdict")},
                     ensure_ascii=False, sort_keys=True))
    return 0 if result["verdict"] == "PASS" else 2


if __name__ == "__main__":
    sys.exit(main())
