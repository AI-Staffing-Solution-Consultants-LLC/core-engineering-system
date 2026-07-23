"""
`track_a` — Python package alias for the `track-a/` source directory.

The repo's source directory is `track-a/` (hyphenated, matching the
project's directory naming convention), but Python module names cannot
contain hyphens. This package bridges the gap: it lives at the repo
root as `track_a/` and re-exports modules from `track-a/` via
importlib, so callers can write `from track_a.opa_eval import
eval_package` in both pytest and standalone Python invocations.

Only modules that need to be importable from outside `track-a/` are
registered here. Currently: `opa_eval`.
"""

import importlib.util
import sys
from pathlib import Path


_THIS_DIR = Path(__file__).resolve().parent
_REPO_ROOT = _THIS_DIR.parent
_TRACK_A_DIR = _REPO_ROOT / "track-a"


def _load_submodule(dotted_name: str, source_path: Path) -> None:
    """Load a single file from track-a/ as a submodule of track_a."""
    if not source_path.is_file():
        return
    spec = importlib.util.spec_from_file_location(dotted_name, source_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[dotted_name] = module
    spec.loader.exec_module(module)
    # Expose as an attribute of the track_a package.
    short_name = dotted_name.rsplit(".", 1)[-1]
    setattr(sys.modules[__name__], short_name, module)


# Register track-a/opa_eval.py as track_a.opa_eval
_load_submodule("track_a.opa_eval", _TRACK_A_DIR / "opa_eval.py")
