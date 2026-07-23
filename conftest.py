"""
Pytest configuration for the core-engineering-system test suite.

Bridges the import path: the source directory is `track-a/` (hyphenated,
matching the repo's directory naming convention), but Python module names
cannot contain hyphens. This conftest synthesizes a `track_a` package
that points at `track-a/` so tests can write `from track_a.opa_eval
import eval_package`.
"""

import importlib.util
import sys
import types
from pathlib import Path


_REPO_ROOT = Path(__file__).resolve().parent
_TRACK_A_DIR = _REPO_ROOT / "track-a"


def _register_track_a_package() -> None:
    """Register `track_a` as an alias for the `track-a/` source directory."""
    if "track_a" in sys.modules:
        return

    track_a_pkg = types.ModuleType("track_a")
    track_a_pkg.__path__ = [str(_TRACK_A_DIR)]
    sys.modules["track_a"] = track_a_pkg

    opa_eval_path = _TRACK_A_DIR / "opa_eval.py"
    if opa_eval_path.is_file():
        spec = importlib.util.spec_from_file_location("track_a.opa_eval", opa_eval_path)
        module = importlib.util.module_from_spec(spec)
        sys.modules["track_a.opa_eval"] = module
        spec.loader.exec_module(module)
        track_a_pkg.opa_eval = module


_register_track_a_package()
