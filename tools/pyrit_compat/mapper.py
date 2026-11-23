"""AST 调用点发现 + 变更映射 + 旧 API/钩子漂移检测。"""
from __future__ import annotations

import ast
import io
import tokenize
from pathlib import Path

from .model import Alert, CallSite, ChangeRecord

HOOK_NAME = "_score_piece_async"


class _ImportVisitor(ast.NodeVisitor):
    def __init__(self, rel_path: str) -> None:
        self.rel_path = rel_path
        self.stack: list[str] = []
        self.sites: list[CallSite] = []

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self.stack.append(node.name)
        self.generic_visit(node)
        self.stack.pop()

    visit_AsyncFunctionDef = visit_FunctionDef  # type: ignore[assignment]

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        self.stack.append(node.name)
        self.generic_visit(node)
        self.stack.pop()

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        module = node.module or ""
        if module == "pyrit" or module.startswith("pyrit."):
            for alias in node.names:
                self.sites.append(CallSite(
                    file=self.rel_path, line=node.lineno, module=module,
                    symbol="%s.%s" % (module, alias.name),
                    function=".".join(self.stack) or "<module>", kind="ImportFrom"))

    def visit_Import(self, node: ast.Import) -> None:
        for alias in node.names:
            if alias.name == "pyrit" or alias.name.startswith("pyrit."):
                self.sites.append(CallSite(
                    file=self.rel_path, line=node.lineno, module=alias.name,
                    symbol=alias.name, function=".".join(self.stack) or "<module>",
                    kind="Import"))
        self.generic_visit(node)


def scan(root: str | Path, include_tests: bool = False) -> list[CallSite]:
    base = Path(root)
    roots = [base / "tools", base / "scripts"]
    if include_tests:
        roots.append(base / "tests")
    sites: list[CallSite] = []
    for source_root in roots:
        if not source_root.exists():
            continue
        for path in sorted(source_root.rglob("*.py")):
            if "__pycache__" in path.parts or "pyrit_compat" in path.parts:
                continue  # 框架自身的探针不是技能调用点
            try:
                tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            except (SyntaxError, UnicodeDecodeError):
                continue
            visitor = _ImportVisitor(path.relative_to(base).as_posix())
            visitor.visit(tree)
            sites.extend(visitor.sites)
    return sites


def _matches(site_symbol: str, change_symbol: str) -> bool:
    return (site_symbol == change_symbol
            or change_symbol.startswith(site_symbol + ".")
            or site_symbol.startswith(change_symbol + "."))


def classify(sites: list[CallSite], records: list[ChangeRecord],
             signatures: dict) -> list[dict]:
    inventory = set(signatures.get("symbols", {}))
    output: list[dict] = []
    for site in sites:
        if site.symbol == "pyrit":  # 版本守卫 import，非对象图调用；先短路避免匹配全部变更
            matched = []
            status = "known-unchanged"
            output.append({"site": site.to_dict(), "status": status, "change_ids": matched})
            continue
        matched = [r.id for r in records if _matches(site.symbol, r.symbol)]
        if matched:
            status = "mapped"
        elif any(_matches(site.symbol, known) for known in inventory):
            status = "known-unchanged"
        else:
            status = "unclassified"
        output.append({"site": site.to_dict(), "status": status, "change_ids": matched})
    return output


def coverage(rows: list[dict]) -> dict:
    total = len(rows)
    classified = sum(1 for r in rows if r["status"] != "unclassified")
    return {
        "total_sites": total,
        "classified_sites": classified,
        "unclassified_sites": total - classified,
        "coverage": (classified / total) if total else 1.0,
    }


def legacy_alerts(root: str | Path) -> list[Alert]:
    base = Path(root)
    alerts: list[Alert] = []
    for source_root in (base / "tools", base / "scripts"):
        if not source_root.exists():
            continue
        for path in sorted(source_root.rglob("*.py")):
            if "pyrit_compat" in path.parts:  # 框架自身含禁用名说明文本，不是调用点
                continue
            text = path.read_text(encoding="utf-8", errors="replace")
            # tokenize 而非文本正则：文档字符串/注释中的禁令说明不是调用点。
            names = [(t.type, t.string, t.start[0])
                     for t in tokenize.generate_tokens(io.StringIO(text).readline)
                     if t.type == tokenize.NAME]
            found: set[tuple[str, int, str]] = set()
            for index, (_type, value, line) in enumerate(names):
                code = ""
                if (value == "pyrit" and index + 2 < len(names)
                        and names[index + 1][1] == "."
                        and names[index + 2][1] == "orchestrator"):
                    code = "pyrit.orchestrator"
                elif value == "AzureOpenAIChatTarget":
                    code = value
                elif value.endswith("Orchestrator") and len(value) > len("Orchestrator"):
                    code = value
                if code:
                    found.add((code, line, path.relative_to(base).as_posix()))
            for code, line, rel in sorted(found):
                alerts.append(Alert(
                    severity="error", code="LEGACY_API",
                    message="legacy PyRIT API in runtime code: %s" % code,
                    file=rel, line=line))
    return alerts


def hook_alerts(root: str | Path) -> list[Alert]:
    base = Path(root)
    alerts: list[Alert] = []
    source_root = base / "tools"
    if not source_root.exists():
        return alerts
    for path in sorted(source_root.rglob("*.py")):
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        except (SyntaxError, UnicodeDecodeError):
            continue
        for node in ast.walk(tree):
            if not isinstance(node, ast.ClassDef):
                continue
            bases = [getattr(b, "id", getattr(b, "attr", "")) for b in node.bases]
            if not any(b.endswith("MessageScorer") for b in bases):
                continue
            for child in ast.walk(node):
                if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)) and child.name == HOOK_NAME:
                    alerts.append(Alert(
                        severity="error", code="SCORER_HOOK_REMOVED",
                        message=("custom MessageScorer overrides _score_piece_async; "
                                 "1.2.0 requires _score_piece_with_expectation_async"),
                        file=path.relative_to(base).as_posix(), line=child.lineno))
    return alerts
