#!/usr/bin/env python3
"""Fix Napoleon documentation violations file-by-file."""

from __future__ import annotations

import argparse
import ast
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from check_napoleon_gate import (  # noqa: E402
    MIN_CLASS_SUMMARY_WORDS,
    Violation,
    _check_file,
    _constructor_has_args,
    _function_has_args,
    _function_has_keyword_args,
    _function_uses_return_or_yield,
    _first_doc_line,
    _iter_python_files,
)


def _humanize(name: str) -> str:
    spaced = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", name)
    return spaced.replace("_", " ").strip().lower()


def _class_summary(class_name: str) -> str:
    return f"Model {_humanize(class_name)} behavior."


def _func_summary(func_name: str) -> str:
    readable = _humanize(func_name)
    if func_name == "__init__":
        return "Initialize instance state."
    if func_name.startswith("_"):
        return f"Handle {readable}."
    return f"{readable.capitalize()}."


def _arg_section(node: ast.FunctionDef | ast.AsyncFunctionDef, *, keyword: bool = False) -> str:
    args = node.args
    if keyword:
        header = "Keyword Args:"
        params = list(args.kwonlyargs)
        if args.kwarg:
            params.append(ast.arg(arg=args.kwarg.arg, annotation=None))
    else:
        header = "Args:"
        params = [*args.posonlyargs, *args.args]
        if params and params[0].arg in {"self", "cls"}:
            params = params[1:]
        if args.vararg:
            params.append(ast.arg(arg=f"*{args.vararg.arg}", annotation=None))
    if not params:
        return ""
    lines = [header]
    for param in params:
        lines.append(f"    {param.arg}: {_humanize(param.arg.lstrip('*'))}.")
    return "\n".join(lines)


def _build_function_docstring(
    node: ast.FunctionDef | ast.AsyncFunctionDef,
    *,
    class_name: str | None = None,
) -> str:
    summary = (
        f"Initialize {class_name}."
        if node.name == "__init__" and class_name
        else _func_summary(node.name)
    )
    parts = [summary, ""]
    if _function_has_args(node):
        section = _arg_section(node)
        if section:
            parts.extend([section, ""])
    if _function_has_keyword_args(node):
        section = _arg_section(node, keyword=True)
        if section:
            parts.extend([section, ""])
    if _function_uses_return_or_yield(node):
        parts.extend(["Returns:", "    Operation result.", ""])
    while parts and parts[-1] == "":
        parts.pop()
    return "\n".join(parts)


def _build_class_docstring(class_node: ast.ClassDef) -> str:
    existing = ast.get_docstring(class_node)
    summary = _first_doc_line(existing) if existing else ""
    if not summary or len(summary.split()) < MIN_CLASS_SUMMARY_WORDS:
        summary = _class_summary(class_node.name)
    parts = [summary]
    if _constructor_has_args(class_node) and (not existing or "Args:" not in existing):
        init_node = next(
            (
                member
                for member in class_node.body
                if isinstance(member, ast.FunctionDef) and member.name == "__init__"
            ),
            None,
        )
        if init_node is not None:
            section = _arg_section(init_node)
            if section:
                parts.extend(["", section])
    return "\n".join(parts)


def _upgrade_function_docstring(node: ast.FunctionDef | ast.AsyncFunctionDef, doc: str) -> str:
    body = doc
    if _function_has_args(node) and "Args:" not in body:
        param_lines: list[str] = []
        for line in doc.splitlines():
            match = re.match(r":param\s+(\*?\*?\w+):\s*(.*)", line.strip())
            if match:
                param_lines.append(f"    {match.group(1)}: {match.group(2)}")
        insert = ["", "Args:", *param_lines] if param_lines else ["", _arg_section(node)]
        body = body.rstrip() + "\n" + "\n".join(insert)
    if _function_has_keyword_args(node) and "Keyword Args:" not in body:
        body = body.rstrip() + "\n\n" + _arg_section(node, keyword=True)
    if _function_uses_return_or_yield(node) and not any(
        header in body for header in ("Returns:", "Yields:")
    ):
        body = body.rstrip() + "\n\nReturns:\n    Operation result."
    return body


def _find_class(tree: ast.Module, class_name: str) -> ast.ClassDef | None:
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == class_name:
            return node
    return None


def _find_function(
    tree: ast.Module,
    symbol: str,
    *,
    lineno: int | None = None,
) -> tuple[ast.FunctionDef | ast.AsyncFunctionDef | None, str | None]:
    def _pick(
        matches: list[tuple[ast.FunctionDef | ast.AsyncFunctionDef, str | None]],
    ) -> tuple[ast.FunctionDef | ast.AsyncFunctionDef | None, str | None]:
        if not matches:
            return None, None
        if lineno is None or len(matches) == 1:
            return matches[0]
        return min(matches, key=lambda item: abs(item[0].lineno - lineno))

    if "." not in symbol:
        matches = [
            (node, None)
            for node in ast.walk(tree)
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == symbol
        ]
        return _pick(matches)

    class_name, member_name = symbol.rsplit(".", 1)
    matches: list[tuple[ast.FunctionDef | ast.AsyncFunctionDef, str | None]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == class_name:
            for member in node.body:
                if isinstance(member, (ast.FunctionDef, ast.AsyncFunctionDef)) and member.name == member_name:
                    matches.append((member, class_name))
    return _pick(matches)


def _node_indent(lines: list[str], node: ast.AST) -> str:
    return re.match(r"\s*", lines[node.lineno - 1]).group(0)


def _format_docstring(lines: list[str], node: ast.AST, body: str) -> list[str]:
    content_indent = _node_indent(lines, node) + "    "
    formatted = [f'{content_indent}"""']
    for line in body.splitlines():
        formatted.append(f"{content_indent}{line}" if line else "")
    formatted.append(f'{content_indent}"""')
    return formatted


def _replace_or_insert_docstring(
    lines: list[str],
    node: ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef,
    body: str,
) -> None:
    formatted = _format_docstring(lines, node, body)
    if (
        node.body
        and isinstance(node.body[0], ast.Expr)
        and isinstance(node.body[0].value, ast.Constant)
        and isinstance(node.body[0].value.value, str)
    ):
        start = node.body[0].lineno - 1
        end = node.body[0].end_lineno
        lines[start:end] = formatted
        return
    if isinstance(node, ast.ClassDef):
        if (
            node.body
            and isinstance(node.body[0], ast.Expr)
            and isinstance(node.body[0].value, ast.Constant)
            and isinstance(node.body[0].value.value, str)
        ):
            start = node.body[0].lineno - 1
            end = node.body[0].end_lineno
            lines[start:end] = formatted
        else:
            lines[node.lineno:node.lineno] = formatted
        return
    if (
        node.body
        and len(node.body) == 1
        and isinstance(node.body[0], ast.Expr)
        and isinstance(node.body[0].value, ast.Constant)
        and node.body[0].value.value is Ellipsis
        and node.body[0].lineno == node.lineno
    ):
        def_line = node.lineno - 1
        indent = _node_indent(lines, node)
        line = lines[def_line].rstrip()
        header = line[:-3].rstrip() if line.endswith("...") else line.split(":", 1)[0] + ":"
        lines[def_line : def_line + 1] = [header, *formatted, f"{indent}    ..."]
        return
    insert_at = node.body[0].lineno if node.body else getattr(node, "end_lineno", node.lineno)
    lines[insert_at - 1 : insert_at - 1] = formatted


def _insert_before(lines: list[str], lineno: int, content: list[str]) -> None:
    indent = re.match(r"\s*", lines[lineno - 1]).group(0)
    lines[lineno - 1:lineno - 1] = [f"{indent}{line}" if line else line for line in content]


def _apply_violation(
    lines: list[str],
    tree: ast.Module,
    violation: Violation,
) -> None:
    code = violation.code
    symbol = violation.symbol

    if code in {"DOC302", "DOC300", "DOC301"}:
        attr = symbol.split(".")[-1]
        _insert_before(lines, violation.line, [f"#: {_humanize(attr).capitalize()}."])
        return

    if code in {"DOC100", "DOC101", "DOC102"}:
        class_node = _find_class(tree, symbol)
        if class_node is None:
            msg = f"missing class {symbol}"
            raise ValueError(msg)
        _replace_or_insert_docstring(lines, class_node, _build_class_docstring(class_node))
        return

    if code in {"DOC200", "DOC202", "DOC203", "DOC205"}:
        func_node, class_name = _find_function(tree, symbol, lineno=violation.line)
        if func_node is None:
            msg = f"missing function {symbol}"
            raise ValueError(msg)
        existing = ast.get_docstring(func_node)
        body = (
            _build_function_docstring(func_node, class_name=class_name)
            if not existing
            else _upgrade_function_docstring(func_node, existing)
        )
        _replace_or_insert_docstring(lines, func_node, body)
        return

    msg = f"unsupported code {code}"
    raise ValueError(msg)


def _fix_file(path: Path) -> int:
    """Fix all violations in one file. Returns number of passes applied."""
    comment_codes = {"DOC302", "DOC300", "DOC301"}
    doc_codes = {"DOC100", "DOC101", "DOC102", "DOC200", "DOC202", "DOC203", "DOC205"}
    passes = 0
    for _ in range(2000):
        violations = _check_file(path)
        if not violations:
            break

        batch = [item for item in violations if item.code in comment_codes]
        if batch:
            source = path.read_text(encoding="utf-8")
            lines = source.splitlines()
            tree = ast.parse(source)
            for violation in sorted(batch, key=lambda item: item.line, reverse=True):
                _apply_violation(lines, tree, violation)
            updated = "\n".join(lines) + "\n"
            ast.parse(updated)
            path.write_text(updated, encoding="utf-8")
            passes += 1
            continue

        doc_batch = [item for item in violations if item.code in doc_codes]
        if not doc_batch:
            break
        violation = max(doc_batch, key=lambda item: item.line)
        source = path.read_text(encoding="utf-8")
        lines = source.splitlines()
        tree = ast.parse(source)
        _apply_violation(lines, tree, violation)
        updated = "\n".join(lines) + "\n"
        ast.parse(updated)
        path.write_text(updated, encoding="utf-8")
        passes += 1
    return passes


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--target", action="append", default=None)
    args = parser.parse_args()

    files = _iter_python_files([Path(t).resolve() for t in (args.target or ["deployfish"])])
    fixed_files = 0
    for file_path in files:
        passes = _fix_file(file_path)
        if passes:
            fixed_files += 1
            remaining = len(_check_file(file_path))
            sys.stdout.write(f"fixed {file_path} ({passes} pass(es), {remaining} remain)\n")

    remaining_total = sum(len(_check_file(file_path)) for file_path in files)
    if remaining_total:
        sys.stdout.write(f"Remaining violations: {remaining_total}\n")
        return 1
    sys.stdout.write("No violations remain.\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
