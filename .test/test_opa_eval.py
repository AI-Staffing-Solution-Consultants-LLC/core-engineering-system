"""
Tests for track-a/opa_eval.py — Rego file structure parser.

These tests verify that eval_package() correctly extracts the structural
elements of a Rego file (package, imports, rules) without actually evaluating
the policy logic. The parser is a stub for future OPA integration.
"""

from pathlib import Path

import pytest

from track_a.opa_eval import eval_package


REPO_ROOT = Path(__file__).resolve().parent.parent
POLICY_FILE = REPO_ROOT / "policy" / "log-reasoning-steps.rego"


def test_eval_package_returns_dict_with_required_keys():
    """eval_package() must return a dict containing package, rules, imports."""
    result = eval_package(str(POLICY_FILE))
    assert isinstance(result, dict)
    assert "package" in result
    assert "rules" in result
    assert "imports" in result


def test_eval_package_extracts_package_name():
    """The package declaration 'package core.constitutional' must be parsed."""
    result = eval_package(str(POLICY_FILE))
    assert result["package"] == "core.constitutional"


def test_eval_package_extracts_deny_rule():
    """The 'deny' rule must appear in the parsed rules list."""
    result = eval_package(str(POLICY_FILE))
    rule_names = [r["name"] for r in result["rules"]]
    assert "deny" in rule_names


def test_eval_package_imports_is_list():
    """imports must be a list (possibly empty for files with no imports)."""
    result = eval_package(str(POLICY_FILE))
    assert isinstance(result["imports"], list)


def test_eval_package_raises_for_missing_file(tmp_path):
    """A missing file path must raise a clear error rather than silently returning empty."""
    missing = tmp_path / "does-not-exist.rego"
    with pytest.raises((FileNotFoundError, OSError)):
        eval_package(str(missing))
