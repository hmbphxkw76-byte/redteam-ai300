"""兼容层：数据驱动的显式适配与显式失败；禁止静默回退。"""
from __future__ import annotations

from importlib import metadata
from typing import Any

from .alert import emit
from .model import Alert
from .version import Version

_RULES: list[dict[str, Any]] | None = None


class CompatibilityError(RuntimeError):
    """未映射或不受支持的 PyRIT API 形态；必须由调用方显式处理。"""


def configure_rules(rules: list[dict[str, Any]]) -> None:
    """由事实文件注入规则；新版本只登记规则，不改本模块。"""
    global _RULES
    _RULES = list(rules)


def get_rules() -> list[dict[str, Any]]:
    global _RULES
    if _RULES is None:
        from .manifest import load_bundle
        _RULES = load_bundle().adapters
    return _RULES


def reset_rules() -> None:
    global _RULES
    _RULES = None


def require_runtime_version(expected: str, *, allow_offline_stub: bool = False) -> Alert:
    """校验已安装发行版版本；离线桩模式仅允许无发行版元数据的测试。"""
    try:
        installed = metadata.version("pyrit")
    except metadata.PackageNotFoundError:
        if allow_offline_stub:
            return Alert("info", "PYRIT_METADATA_ABSENT",
                         "pyrit metadata absent; offline stub mode, version not verified")
        raise CompatibilityError("PyRIT 未安装；需要 pyrit==%s" % expected)
    if Version(installed) != Version(expected):
        raise CompatibilityError(
            "PyRIT 版本不匹配：期望 %s，实际 %s；源见 data/versions/<version>.json"
            % (expected, installed))
    return Alert("info", "PYRIT_VERSION_OK", "pyrit==%s verified" % expected)


def _rule_matches(rule: dict[str, Any], symbol: str) -> bool:
    target = rule["symbol"]
    return symbol == target or symbol.startswith(target + ".") or target.startswith(symbol + ".")


def resolve_import(module: str, name: str, version: str) -> tuple[str, str]:
    """模块迁移由规则驱动；永久禁用的 0.x 名称保留硬守卫。"""
    symbol = "%s.%s" % (module, name)
    for rule in get_rules():
        if not _rule_matches(rule, symbol):
            continue
        for action in rule["actions"]:
            if action["kind"] == "reject":
                raise CompatibilityError("%s 已移除：%s" % (symbol, action.get("reason", "")))
    if module == "pyrit.orchestrator":
        raise CompatibilityError("pyrit.orchestrator 已移除；使用 pyrit.executor.attack 的 *Attack")
    if name.endswith("Orchestrator") or name == "AzureOpenAIChatTarget":
        raise CompatibilityError("%s 属于 0.x 旧名" % name)
    return module, name


def adapt_kwargs(symbol: str, kwargs: dict[str, Any], version: str
                 ) -> tuple[dict[str, Any], list[Alert]]:
    """按登记规则适配参数；任何改写都产生 warn/error，绝不静默。"""
    result = dict(kwargs)
    alerts: list[Alert] = []
    v = Version(version)
    matched = [r for r in get_rules()
               if _rule_matches(r, symbol) and Version(r.get("since", "1.1.0")) <= v
               and (not r.get("until") or v < Version(r["until"]))]
    if not matched:
        raise CompatibilityError("no adapter rule registered for %s@%s" % (symbol, version))

    for rule in matched:
        for action in rule["actions"]:
            kind = action["kind"]
            if kind == "reject":
                raise CompatibilityError("%s：%s" % (symbol, action.get("reason", "unsupported")))
            param = action["param"]
            if kind == "reject_param" and param in result:
                raise CompatibilityError(
                    "%s(%s=...) 不受支持；改用 %s"
                    % (symbol, param, action.get("replacement", "supported API")))
            if kind == "require_param" and param not in result:
                raise CompatibilityError("%s 缺少必填参数 %s" % (symbol, param))
            if kind == "require_min_version" and param in result:
                since = Version(action["since"])
                if v < since:
                    raise CompatibilityError("%s.%s 自 %s 起才支持，当前 %s"
                                             % (symbol, param, since, version))
                alerts.append(Alert("info", "PARAM_ADDED",
                                    "%s.%s 自 %s 起可用" % (symbol, param, since)))
            if (kind == "rewrite_param" and param in result
                    and result[param] == action.get("from")
                    and v >= Version(action.get("since", "1.1.0"))):
                result[param] = action["to"]
                alerts.append(Alert("warn", "PARAM_REWRITTEN",
                                    "%s.%s: %s → %s（规则 %s）"
                                    % (symbol, param, action["from"], action["to"], rule["id"])))
    if "timeout" in result:
        alerts.append(Alert("info", "HTTPTIMEOUT_PASSTHROUGH",
                            "timeout 经 **httpx_client_kwargs 透传"))
    return result, alerts


def signature_alerts(signatures: dict, baseline: str, target: str) -> list[Alert]:
    """签名快照比对：新增/移除/默认值变化均产生可读告警。"""
    alerts: list[Alert] = []
    table = signatures.get("symbols", signatures)
    for symbol, versions in table.items():
        old = versions.get(baseline)
        new = versions.get(target)
        if not old or not new:
            alerts.append(Alert("error", "SIGNATURE_SNAPSHOT_MISSING",
                                "%s 缺少 %s 或 %s 签名快照" % (symbol, baseline, target)))
            continue
        if old.get("kind") != new.get("kind"):
            alerts.append(Alert("warn", "SIGNATURE_REPRESENTATION_CHANGED",
                                "%s 签名表示方式变化（%s → %s）"
                                % (symbol, old.get("kind"), new.get("kind"))))
            continue
        if new.get("kind") == "passthrough-wrapper":
            continue
        removed = sorted(set(old["params"]) - set(new["params"]))
        added = sorted(set(new["params"]) - set(old["params"]))
        if removed:
            alerts.append(Alert("error", "PARAM_REMOVED",
                                "%s 参数移除：%s" % (symbol, ", ".join(removed))))
        if added:
            alerts.append(Alert("warn", "PARAM_ADDED",
                                "%s 参数新增：%s" % (symbol, ", ".join(added))))
        defaults_old = old.get("defaults", {})
        defaults_new = new.get("defaults", {})
        for key in sorted(set(defaults_old) & set(defaults_new)):
            if defaults_old[key] != defaults_new[key]:
                alerts.append(Alert("warn", "DEFAULT_CHANGED",
                                    "%s.%s 默认值 %s → %s"
                                    % (symbol, key, defaults_old[key], defaults_new[key])))
    return alerts


def report(alert: Alert) -> None:
    emit(alert)
