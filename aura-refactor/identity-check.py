#!/usr/bin/env python3
"""Identity check: verify zero 'atlas_' references remain in a directory tree.

Scans file names, directory names, and file contents for any remaining 'atlas_'
substring. Exits 0 if clean, exits 1 if any reference found.

Usage:
    python3 identity-check.py --target-path /path/to/project
"""

import argparse
import os
import sys
from pathlib import Path

DEFAULT_EXCLUDES = {"vendor", "node_modules", ".git"}
ATLAS_PREFIX = "atlas_"


def _is_excluded(path: Path, excludes: set[str]) -> bool:
    """Check if any part of the path matches an exclude pattern."""
    parts = set(path.parts)
    return bool(parts & excludes)


def check(target_path: str, excludes: set[str] | None = None) -> int:
    """Scan for remaining atlas_ references. Returns count of violations found."""
    root = Path(target_path).resolve()
    if not root.exists():
        print(f"ERROR: target path does not exist: {root}", file=sys.stderr)
        return -1

    exclude_set = DEFAULT_EXCLUDES | (excludes or set())
    violations = []

    # Walk the tree
    for dirpath_str, dirnames, filenames in os.walk(root):
        dirpath = Path(dirpath_str)
        if _is_excluded(dirpath, exclude_set):
            dirnames.clear()
            continue

        # Check directory name
        if ATLAS_PREFIX in dirpath.name:
            violations.append(f"[DIRNAME] {dirpath}")

        # Check file names and contents
        for filename in filenames:
            filepath = dirpath / filename
            if _is_excluded(filepath, exclude_set):
                continue

            # File name check
            if ATLAS_PREFIX in filename:
                violations.append(f"[FILENAME] {filepath}")

            # File content check
            try:
                content = filepath.read_text()
            except (UnicodeDecodeError, PermissionError, OSError):
                continue

            if ATLAS_PREFIX in content:
                lines = [
                    f"  L{i + 1}: {line.rstrip()}"
                    for i, line in enumerate(content.splitlines())
                    if ATLAS_PREFIX in line
                ]
                violations.append(f"[CONTENT] {filepath}:")
                violations.extend(lines)

    if violations:
        print(
            f"FAIL: Found {len(violations)} violation(s) containing '{ATLAS_PREFIX}':"
        )
        for v in violations:
            print(v)
        return len(violations)

    print(f"PASS: No '{ATLAS_PREFIX}' references found in {root}")
    return 0


def main():
    parser = argparse.ArgumentParser(
        description="Verify zero atlas_ references remain in a directory tree."
    )
    parser.add_argument("--target-path", required=True, help="Root directory to scan")
    parser.add_argument(
        "--exclude",
        action="append",
        default=[],
        dest="extra_excludes",
        help="Additional directory patterns to exclude (repeatable)",
    )
    args = parser.parse_args()

    extra_excludes = set(args.extra_excludes) if args.extra_excludes else set()
    violation_count = check(
        target_path=args.target_path,
        excludes=extra_excludes,
    )
    sys.exit(0 if violation_count == 0 else 1)


if __name__ == "__main__":
    main()
