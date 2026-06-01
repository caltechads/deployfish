from __future__ import annotations

import argparse
import ast
import json
import sys
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path

RETURNS_SECTIONS = ("Returns:", "Yields:")
MIN_CLASS_SUMMARY_WORDS = 3


@dataclass(frozen=True)
class Violation:
    """One doc quality violation."""

    path: str
    line: int
    code: str
    symbol: str
    message: str

    @property
    def key(self) -> str:
        """Stable identity key used by baseline filtering."""
        return f"{self.path}:{self.line}:{self.code}:{self.symbol}"


def _is_test_path(path: Path) -> bool:
    """Return whether a path belongs to tests."""
    return "tests" in path.parts or path.name.startswith("test_")


def _iter_python_files(targets: list[Path]) -> list[Path]:
    """Yield python files under targets, excluding tests."""
    files: list[Path] = []
    for target in targets:
        if not target.exists():
            continue
        if target.is_file() and target.suffix == ".py" and not _is_test_path(target):
            files.append(target)
            continue
        for path in sorted(target.rglob("*.py")):
            if _is_test_path(path):
                continue
            files.append(path)
    return files


def _has_doc_comment(lines: list[str], lineno: int) -> bool:
    """Check for a Napoleon ``#:`` doc comment inline or directly above."""
    if lineno <= 0 or lineno > len(lines):
        return False

    current = lines[lineno - 1]
    if "#:" in current:
        return True

    index = lineno - 2
    while index >= 0:
        text = lines[index].strip()
        if not text:
            index -= 1
            continue
        if text.startswith("#:"):
            return True
        if text.startswith("#"):
            index -= 1
            continue
        break
    return False


def _first_doc_line(docstring: str | None) -> str:
    """Return first non-empty docstring line."""
    if not docstring:
        return ""
    for raw in docstring.splitlines():
        line = raw.strip()
        if line:
            return line
    return ""


def _iter_class_attributes(class_node: ast.ClassDef) -> list[tuple[str, int]]:
    """Yield class attribute names and line numbers."""
    attributes: list[tuple[str, int]] = []
    for node in class_node.body:
        if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            attributes.append((node.target.id, node.lineno))
        elif isinstance(node, ast.Assign):
            attributes.extend(
                (target.id, node.lineno)
                for target in node.targets
                if isinstance(target, ast.Name)
            )
    return attributes


def _iter_module_globals(module: ast.Module) -> list[tuple[str, int]]:
    """Yield module-level global variables and line numbers."""
    globals_: list[tuple[str, int]] = []
    for node in module.body:
        if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            globals_.append((node.target.id, node.lineno))
        elif isinstance(node, ast.Assign):
            globals_.extend(
                (target.id, node.lineno)
                for target in node.targets
                if isinstance(target, ast.Name)
            )
    return globals_


def _iter_init_instance_attrs(init_node: ast.FunctionDef) -> list[tuple[str, int]]:
    """Yield ``self.<attr>`` assignments in ``__init__``."""
    self_name = init_node.args.args[0].arg if init_node.args.args else "self"
    attrs: list[tuple[str, int]] = []
    for node in ast.walk(init_node):
        if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Attribute):
            target = node.target
            if isinstance(target.value, ast.Name) and target.value.id == self_name:
                attrs.append((target.attr, node.lineno))
        elif isinstance(node, ast.Assign):
            for assign_target in node.targets:
                if not isinstance(assign_target, ast.Attribute):
                    continue
                if (
                    isinstance(assign_target.value, ast.Name)
                    and assign_target.value.id == self_name
                ):
                    attrs.append((assign_target.attr, node.lineno))
    return attrs


def _constructor_has_args(class_node: ast.ClassDef) -> bool:
    """Return whether class ``__init__`` has constructor arguments."""
    for node in class_node.body:
        if not isinstance(node, ast.FunctionDef) or node.name != "__init__":
            continue
        positional = max(0, len(node.args.args) - 1)
        keyword_only = len(node.args.kwonlyargs)
        varargs = 1 if node.args.vararg else 0
        kwargs = 1 if node.args.kwarg else 0
        return positional + keyword_only + varargs + kwargs > 0
    return False


def _function_has_args(
    node: ast.FunctionDef | ast.AsyncFunctionDef,
) -> bool:
    """Return whether a function defines non-self/cls positional arguments."""
    positional = [*node.args.posonlyargs, *node.args.args]
    if positional and positional[0].arg in {"self", "cls"}:
        positional = positional[1:]
    return bool(positional or node.args.vararg)


def _function_has_keyword_args(
    node: ast.FunctionDef | ast.AsyncFunctionDef,
) -> bool:
    """Return whether a function defines keyword-only or ``**kwargs`` args."""
    return bool(node.args.kwonlyargs or node.args.kwarg)


def _function_uses_return_or_yield(
    node: ast.FunctionDef | ast.AsyncFunctionDef,
) -> bool:
    """
    Return whether function body yields or returns a non-``None`` value.

    Nested function/class scopes are ignored for this determination.
    """
    stack: list[ast.AST] = [*node.body]
    while stack:
        current = stack.pop()
        if isinstance(current, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            continue
        if isinstance(current, (ast.Yield, ast.YieldFrom)):
            return True
        if isinstance(current, ast.Return):
            if current.value is None:
                continue
            if isinstance(current.value, ast.Constant) and current.value.value is None:
                continue
            return True
        stack.extend(ast.iter_child_nodes(current))
    return False


def _check_function_doc(
    path: Path,
    node: ast.FunctionDef | ast.AsyncFunctionDef,
    *,
    symbol: str,
) -> list[Violation]:
    """Validate Napoleon sections on one function or method."""
    violations: list[Violation] = []
    doc = ast.get_docstring(node)

    if not doc:
        violations.append(
            Violation(
                path=str(path),
                line=node.lineno,
                code="DOC200",
                symbol=symbol,
                message="Missing docstring on function/method.",
            )
        )
        return violations

    if _function_has_args(node) and "Args:" not in doc:
        violations.append(
            Violation(
                path=str(path),
                line=node.lineno,
                code="DOC202",
                symbol=symbol,
                message="Missing required Napoleon section 'Args:'.",
            )
        )

    if _function_has_keyword_args(node) and "Keyword Args:" not in doc:
        violations.append(
            Violation(
                path=str(path),
                line=node.lineno,
                code="DOC203",
                symbol=symbol,
                message="Missing required Napoleon section 'Keyword Args:'.",
            )
        )

    if _function_uses_return_or_yield(node) and not any(
        header in doc for header in RETURNS_SECTIONS
    ):
        violations.append(
            Violation(
                path=str(path),
                line=node.lineno,
                code="DOC205",
                symbol=symbol,
                message=(
                    "Missing required Napoleon section 'Returns:' or 'Yields:' "
                    "for function with yielded/returned value."
                ),
            )
        )

    return violations


def _check_file(path: Path) -> list[Violation]:  # noqa: PLR0912
    """Run all doc-quality checks for one source file."""
    source = path.read_text(encoding="utf-8")
    lines = source.splitlines()
    tree = ast.parse(source)

    violations: list[Violation] = []

    for name, lineno in _iter_module_globals(tree):
        if name.startswith("__") and name.endswith("__"):
            continue
        if not _has_doc_comment(lines, lineno):
            violations.append(
                Violation(
                    path=str(path),
                    line=lineno,
                    code="DOC302",
                    symbol=name,
                    message="Module-level global variable missing '#:' documentation.",
                )
            )

    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            violations.extend(_check_function_doc(path, node, symbol=node.name))
            continue

        if not isinstance(node, ast.ClassDef):
            continue

        class_doc = ast.get_docstring(node)
        first_line = _first_doc_line(class_doc)
        if not class_doc:
            violations.append(
                Violation(
                    path=str(path),
                    line=node.lineno,
                    code="DOC100",
                    symbol=node.name,
                    message="Missing class docstring.",
                )
            )
        else:
            if len(first_line.split()) < MIN_CLASS_SUMMARY_WORDS:
                violations.append(
                    Violation(
                        path=str(path),
                        line=node.lineno,
                        code="DOC102",
                        symbol=node.name,
                        message=(
                            "Class docstring summary is too brief to describe "
                            "class contract."
                        ),
                    )
                )
            if _constructor_has_args(node) and "Args:" not in class_doc:
                violations.append(
                    Violation(
                        path=str(path),
                        line=node.lineno,
                        code="DOC101",
                        symbol=node.name,
                        message=(
                            "Class with constructor arguments must document Args: "
                            "in class docstring."
                        ),
                    )
                )

        for attr_name, lineno in _iter_class_attributes(node):
            if not _has_doc_comment(lines, lineno):
                violations.append(
                    Violation(
                        path=str(path),
                        line=lineno,
                        code="DOC300",
                        symbol=f"{node.name}.{attr_name}",
                        message="Class attribute missing '#:' documentation.",
                    )
                )

        for member in node.body:
            if isinstance(member, (ast.FunctionDef, ast.AsyncFunctionDef)):
                violations.extend(
                    _check_function_doc(
                        path, member, symbol=f"{node.name}.{member.name}"
                    )
                )
                if isinstance(member, ast.FunctionDef) and member.name == "__init__":
                    for attr_name, lineno in _iter_init_instance_attrs(member):
                        if _has_doc_comment(lines, lineno):
                            continue
                        violations.append(
                            Violation(
                                path=str(path),
                                line=lineno,
                                code="DOC301",
                                symbol=f"{node.name}.{attr_name}",
                                message=(
                                    "Instance attribute assigned in __init__ "
                                    "is missing '#:' "
                                    "documentation."
                                ),
                            )
                        )

    return violations


def _load_baseline_keys(path: Path) -> set[str]:
    """Load baseline violation keys."""
    if not path.exists():
        return set()
    data = json.loads(path.read_text(encoding="utf-8"))
    return {entry["key"] for entry in data.get("violations", [])}


def _write_baseline(path: Path, violations: list[Violation]) -> None:
    """Persist baseline data."""
    payload = {
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "violation_count": len(violations),
        "violations": [
            {
                "key": violation.key,
                **asdict(violation),
            }
            for violation in violations
        ],
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def _print_violations(title: str, violations: list[Violation]) -> None:
    """Render violations to stdout."""
    print(title)
    for violation in violations:
        print(
            f"{violation.path}:{violation.line} "
            f"{violation.code} {violation.symbol} - {violation.message}"
        )


def main() -> int:
    """CLI entrypoint."""
    parser = argparse.ArgumentParser(description="Napoleon documentation quality gate")
    parser.add_argument(
        "--target",
        action="append",
        default=argparse.SUPPRESS,
        help=(
            "Path to check (can be passed multiple times; defaults to "
            "tfreporter if omitted)"
        ),
    )
    parser.add_argument(
        "--baseline",
        default="doc/quality/napoleon_gate_baseline.json",
        help="Baseline JSON path",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Fail on all violations, ignoring baseline",
    )
    parser.add_argument(
        "--write-baseline",
        action="store_true",
        help="Write baseline from current violations and exit 0",
    )
    args = parser.parse_args()

    raw_targets = getattr(args, "target", None)
    if raw_targets is None:
        raw_targets = ["tfreporter"]
    targets = [Path(item).resolve() for item in raw_targets]
    baseline_path = Path(args.baseline).resolve()

    violations: list[Violation] = []
    for file in _iter_python_files(targets):
        violations.extend(_check_file(file))

    violations.sort(key=lambda item: (item.path, item.line, item.code, item.symbol))

    if args.write_baseline:
        _write_baseline(baseline_path, violations)
        print(
            f"Wrote baseline with {len(violations)} violations to {baseline_path}"
        )
        return 0

    if args.strict:
        if violations:
            _print_violations("Strict mode violations:", violations)
            print(f"Found {len(violations)} total violations.")
            return 1
        print("No doc-quality violations found in strict mode.")
        return 0

    baseline_keys = _load_baseline_keys(baseline_path)
    if not baseline_path.exists():
        print(
            "No baseline found. Run with --write-baseline first or use --strict.",
            file=sys.stderr,
        )
        return 2

    new_violations = [item for item in violations if item.key not in baseline_keys]
    if new_violations:
        _print_violations("New violations (not in baseline):", new_violations)
        print(
            f"Found {len(new_violations)} new violations "
            f"({len(violations)} total, {len(baseline_keys)} baseline keys)."
        )
        return 1

    print(
        "Napoleon gate passed: no new violations "
        f"({len(violations)} total, {len(baseline_keys)} baseline keys)."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
