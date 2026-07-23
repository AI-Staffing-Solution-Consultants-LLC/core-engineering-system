"""
Rego file structure parser for the core-engineering-system.

This module provides a lightweight parser for Rego (.rego) policy files.
It extracts the structural elements — package declaration, imports, and
rule definitions — without actually evaluating the policy logic.

This is a stub for future OPA integration. The Constitutional AI policies
in policy/*.rego are currently documentation-of-intent; neither Track A
nor Track B evaluates them at runtime. This parser gives Track A the
ability to introspect policy files (e.g., for validation, linting, or
future enforcement) without pulling in the full opa-python dependency.

Parsing strategy:
  - Strip line comments (lines starting with '#').
  - Match `package <dotted.name>` for the package declaration.
  - Match `import <path>` (with optional `as <alias>`) for imports.
  - Match `<rule_name>[<key>] { <body> }` for rule definitions, where
    the body is captured by brace-balancing rather than regex alone
    (Rego bodies can contain nested braces in expressions).
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any


_PACKAGE_RE = re.compile(r"^\s*package\s+([A-Za-z_][\w.]*)\s*$", re.MULTILINE)
_IMPORT_RE = re.compile(
    r"^\s*import\s+([A-Za-z_][\w.]*(?:\.[A-Za-z_]\w*)*)"
    r"(?:\s+as\s+([A-Za-z_]\w*))?\s*$",
    re.MULTILINE,
)
# Rule header: optional key in brackets, then opening brace.
_RULE_HEADER_RE = re.compile(
    r"^\s*([A-Za-z_]\w*)(?:\[([A-Za-z_]\w*)\])?\s*\{",
    re.MULTILINE,
)
# Default rule (no body) — `name := value` or `name = value`.
_DEFAULT_RE = re.compile(r"^\s*([A-Za-z_]\w*)\s*(?::=|=)\s*", re.MULTILINE)


def _strip_comments(source: str) -> str:
    """Remove '#' line comments while preserving line numbers approximately."""
    cleaned_lines = []
    for line in source.splitlines():
        # Strip trailing comment; leave the rest of the line intact.
        hash_idx = line.find("#")
        if hash_idx != -1:
            line = line[:hash_idx]
        cleaned_lines.append(line)
    return "\n".join(cleaned_lines)


def _extract_rule_body(source: str, open_brace_idx: int) -> tuple[str, int]:
    """
    Given the index of an opening '{', return (body_text, end_index) by
    brace-balancing. Handles nested braces in Rego expressions.
    """
    depth = 0
    i = open_brace_idx
    while i < len(source):
        ch = source[i]
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return source[open_brace_idx + 1 : i], i
        i += 1
    # Unterminated rule — return what we have.
    return source[open_brace_idx + 1 :], len(source) - 1


def eval_package(path: str | Path) -> dict[str, Any]:
    """
    Parse a Rego file and return its structural elements.

    Returns a dict with keys:
      - package: str — the package name (e.g., "core.constitutional")
      - imports: list[str] — imported paths (without 'as' aliases)
      - rules: list[dict] — each rule has 'name', optional 'key', and 'body'

    Raises FileNotFoundError if the path does not exist.
    """
    file_path = Path(path)
    if not file_path.is_file():
        raise FileNotFoundError(f"Rego file not found: {file_path}")

    raw = file_path.read_text(encoding="utf-8")
    cleaned = _strip_comments(raw)

    package_name: str | None = None
    imports: list[str] = []
    rules: list[dict[str, Any]] = []

    # Walk line-by-line for package/import/default detection.
    for line in cleaned.splitlines():
        stripped = line.strip()
        if not stripped:
            continue

        pkg_match = _PACKAGE_RE.match(line)
        if pkg_match:
            package_name = pkg_match.group(1)
            continue

        imp_match = _IMPORT_RE.match(line)
        if imp_match:
            imports.append(imp_match.group(1))
            continue

    # Walk the cleaned source for rule headers (with bodies).
    # We scan the full source so multi-line rule headers are handled.
    for match in _RULE_HEADER_RE.finditer(cleaned):
        rule_name = match.group(1)
        rule_key = match.group(2)  # may be None
        open_brace_idx = match.end() - 1  # position of '{'
        body, _ = _extract_rule_body(cleaned, open_brace_idx)
        rules.append(
            {
                "name": rule_name,
                "key": rule_key,
                "body": body.strip(),
            }
        )

    return {
        "package": package_name,
        "imports": imports,
        "rules": rules,
    }
