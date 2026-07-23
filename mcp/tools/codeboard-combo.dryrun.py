#!/usr/bin/env python3
"""
codeboard-combo.dryrun.py — Static skeleton printer for the codeboard-combo MCP tool spec.

This script is INTENTIONALLY config-only. It MUST NOT make any network calls.
The `live: false` flag in codeboard-combo.json is the critical safety mechanism;
flipping it to true requires explicit human approval (checkpoint #10).

Usage:
    python mcp/tools/codeboard-combo.dryrun.py

Exit codes:
    0 — spec loaded and skeleton printed successfully
    1 — spec missing, malformed, or live=true (refuses to run)
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

SPEC_PATH = Path(__file__).resolve().parent / "codeboard-combo.json"


def load_spec(path: Path) -> dict:
    """Load and validate the codeboard-combo spec from disk."""
    if not path.exists():
        print(f"ERROR: spec not found at {path}", file=sys.stderr)
        sys.exit(1)
    try:
        spec = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        print(f"ERROR: spec at {path} is not valid JSON: {exc}", file=sys.stderr)
        sys.exit(1)
    return spec


def assert_config_only(spec: dict) -> None:
    """Refuse to run if the spec is marked live=true."""
    if spec.get("live") is not False:
        print(
            "ERROR: spec.live must be False for dryrun. "
            "Live API calls require explicit human approval (checkpoint #10).",
            file=sys.stderr,
        )
        sys.exit(1)


def render_skeleton(spec: dict) -> str:
    """Render a static skeleton showing inputs, routing, and outputs."""
    name = spec.get("name", "<unnamed>")
    version = spec.get("version", "<unknown>")
    description = spec.get("description", "")
    inputs = spec.get("inputs", {})
    routing = spec.get("routing", {})
    outputs = spec.get("outputs", {})
    backends = spec.get("backends", [])
    env_vars = spec.get("env_vars", [])

    lines = []
    lines.append(f"=== {name} v{version} (config-only skeleton) ===")
    lines.append(f"description: {description}")
    lines.append("")
    lines.append("[inputs]")
    for key, schema in inputs.items():
        required = schema.get("required", False)
        default = schema.get("default", "<none>")
        kind = schema.get("type", "any")
        req_marker = "REQUIRED" if required else "optional"
        lines.append(f"  - {key}: {kind} ({req_marker}, default={default!r})")
    lines.append("")
    lines.append("[routing]")
    for backend, role in routing.items():
        lines.append(f"  - {backend}: {role}")
    lines.append("")
    lines.append("[outputs]")
    for key, kind in outputs.items():
        lines.append(f"  - {key}: {kind}")
    lines.append("")
    lines.append("[backends]")
    for b in backends:
        lines.append(f"  - {b}")
    lines.append("")
    lines.append("[env_vars]")
    for v in env_vars:
        lines.append(
            f"  - {v}  (sourced from Infisical or gcloud secrets, NEVER in-repo .env)"
        )
    lines.append("")
    lines.append("[live]")
    lines.append("  - live: false  (config-only; no network calls performed)")
    lines.append("")
    lines.append("=== skeleton rendered; no live API calls made ===")
    return "\n".join(lines)


def main() -> int:
    spec = load_spec(SPEC_PATH)
    assert_config_only(spec)
    print(render_skeleton(spec))
    return 0


if __name__ == "__main__":
    sys.exit(main())
