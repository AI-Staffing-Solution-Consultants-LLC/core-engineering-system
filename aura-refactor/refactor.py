#!/usr/bin/env python3
"""Recursive rename tool: replace all atlas_ → aura_ in file names, directory
names, and file contents.

Usage:
    python3 refactor.py --target-path /path/to/project
    python3 refactor.py --target-path /path/to/project --dry-run
    python3 refactor.py --target-path /path/to/project --exclude build --exclude dist
"""

import argparse
import os
import sys
from pathlib import Path

DEFAULT_EXCLUDES = {"vendor", "node_modules", ".git"}

ATLAS_PREFIX = "atlas_"
AURA_PREFIX = "aura_"


def _is_excluded(path: Path, excludes: set[str]) -> bool:
    """Check if any part of the path matches an exclude pattern."""
    parts = set(path.parts)
    return bool(parts & excludes)


def _file_needs_content_rename(filepath: Path) -> bool:
    """Check if file content contains atlas_."""
    try:
        content = filepath.read_text()
    except (UnicodeDecodeError, PermissionError, OSError):
        return False
    return ATLAS_PREFIX in content


def _needs_rename(name: str) -> bool:
    """Check if a file or directory name contains atlas_."""
    return ATLAS_PREFIX in name


def _rename_entry(path: Path, new_name: str, dry_run: bool) -> bool:
    """Rename a file or directory, or log it in dry-run mode."""
    new_path = path.parent / new_name
    if dry_run:
        print(f"  [RENAME] {path} → {new_path}")
        return False
    path.rename(new_path)
    print(f"  Renamed: {path} → {new_path}")
    return True


def _replace_content(filepath: Path, dry_run: bool) -> int:
    """Replace atlas_ with aura_ in file content. Returns count of replacements."""
    try:
        original = filepath.read_text()
    except (UnicodeDecodeError, PermissionError, OSError):
        return 0

    if ATLAS_PREFIX not in original:
        return 0

    replacement = original.replace(ATLAS_PREFIX, AURA_PREFIX)
    count = original.count(ATLAS_PREFIX)

    if dry_run:
        print(
            f"  [CONTENT] {filepath}: {count} occurrence(s) of '{ATLAS_PREFIX}' → '{AURA_PREFIX}'"
        )
        return 0

    filepath.write_text(replacement)
    print(f"  Content: {filepath} — {count} replacement(s)")
    return count


def refactor(target_path: str, dry_run: bool = False, excludes: set[str] | None = None):
    """Walk target_path and replace all atlas_ with aura_."""
    root = Path(target_path).resolve()
    if not root.exists():
        print(f"ERROR: target path does not exist: {root}", file=sys.stderr)
        sys.exit(1)

    exclude_set = DEFAULT_EXCLUDES | (excludes or set())

    if dry_run:
        print(f"=== DRY-RUN MODE — no files will be modified ===")
    print(f"Target: {root}")
    print(f"Excludes: {sorted(exclude_set)}")
    print()

    total_content = 0
    total_files = 0
    total_dirs = 0

    # ---- Phase 1: Replace file contents (top-down or any order — path-independent) ----
    print("Phase 1: Replacing file contents...")
    for dirpath_str, dirnames, filenames in os.walk(root):
        dirpath = Path(dirpath_str)
        if _is_excluded(dirpath, exclude_set):
            continue
        for filename in filenames:
            filepath = dirpath / filename
            if _is_excluded(filepath, exclude_set):
                continue
            if _file_needs_content_rename(filepath):
                total_content += _replace_content(filepath, dry_run)

    # ---- Phase 2: Rename files (bottom-up, so nested files are renamed before
    #      their parent directories are renamed) ----
    print("Phase 2: Renaming files...")
    for dirpath_str, dirnames, filenames in os.walk(root, topdown=False):
        dirpath = Path(dirpath_str)
        if _is_excluded(dirpath, exclude_set):
            # Clear dirnames to skip excluded subtrees in subsequent walks
            dirnames.clear()
            continue
        for filename in filenames:
            filepath = dirpath / filename
            if _is_excluded(filepath, exclude_set):
                continue
            if _needs_rename(filename):
                new_filename = filename.replace(ATLAS_PREFIX, AURA_PREFIX)
                if _rename_entry(filepath, new_filename, dry_run):
                    total_files += 1
                elif dry_run:
                    total_files += 1

    # ---- Phase 3: Rename directories (bottom-up — deepest first) ----
    print("Phase 3: Renaming directories...")
    for dirpath_str, dirnames, _ in os.walk(root, topdown=False):
        dirpath = Path(dirpath_str)
        if _is_excluded(dirpath, exclude_set):
            dirnames.clear()
            continue
        if _needs_rename(dirpath.name):
            new_dirname = dirpath.name.replace(ATLAS_PREFIX, AURA_PREFIX)
            if _rename_entry(dirpath, new_dirname, dry_run):
                total_dirs += 1
            elif dry_run:
                total_dirs += 1

    print()
    mode = "would be" if dry_run else "were"
    print(
        f"Summary: {total_content} content replacements, {total_files} file renames, "
        f"{total_dirs} directory renames {mode} performed."
    )


def main():
    parser = argparse.ArgumentParser(
        description="Rename atlas_ → aura_ recursively in files, directories, and contents."
    )
    parser.add_argument(
        "--target-path", required=True, help="Root directory to process"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Report planned changes without modifying anything",
    )
    parser.add_argument(
        "--exclude",
        action="append",
        default=[],
        dest="extra_excludes",
        help="Additional directory patterns to exclude (repeatable)",
    )
    args = parser.parse_args()

    extra_excludes = set(args.extra_excludes) if args.extra_excludes else set()
    refactor(
        target_path=args.target_path,
        dry_run=args.dry_run,
        excludes=extra_excludes,
    )


if __name__ == "__main__":
    main()
