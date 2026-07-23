"""TDD tests for aura-refactor tools: refactor.py and identity-check.py."""

import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

# Paths relative to repo root
REPO_ROOT = Path(__file__).resolve().parent.parent
REFACTOR_SCRIPT = REPO_ROOT / "aura-refactor" / "refactor.py"
IDENTITY_CHECK_SCRIPT = REPO_ROOT / "aura-refactor" / "identity-check.py"


def _py() -> str:
    """Return the python executable path."""
    return sys.executable


def _run_refactor(*args: str, cwd: Path | str) -> subprocess.CompletedProcess:
    """Run refactor.py with given arguments from cwd."""
    return subprocess.run(
        [_py(), str(REFACTOR_SCRIPT), *args],
        cwd=str(cwd),
        capture_output=True,
        text=True,
        timeout=30,
    )


def _run_identity_check(*args: str, cwd: Path | str) -> subprocess.CompletedProcess:
    """Run identity-check.py with given arguments from cwd."""
    return subprocess.run(
        [_py(), str(IDENTITY_CHECK_SCRIPT), *args],
        cwd=str(cwd),
        capture_output=True,
        text=True,
        timeout=30,
    )


def _create_test_fixture(base_dir: Path) -> None:
    """Create a realistic test directory tree with atlas_ references."""
    # Files with atlas_ in name
    (base_dir / "atlas_config.py").write_text("# atlas_config module")
    (base_dir / "atlas_worker.go").write_text("// atlas_worker entry point")

    # Files with atlas_ in content
    (base_dir / "main.py").write_text(
        "import atlas_config\n"
        "atlas_secret = 'abc'\n"
        "def atlas_init():\n"
        "    return atlas_config.load()\n"
    )
    (base_dir / "service.go").write_text(
        "package atlas_service\n\n"
        "type AtlasClient struct { host string }\n"
        "func NewAtlasClient() *AtlasClient {\n"
        "    return &AtlasClient{host: atlas_host_default}\n"
        "}\n"
    )
    (base_dir / "service.go").write_text(
        "package atlas_service\n\n"
        "func NewAtlasClient() *AtlasClient {\n"
        "    return &AtlasClient{host: atlas_host_default}\n"
        "}\n"
    )

    # Directories with atlas_ in name
    atlas_lib = base_dir / "atlas_lib"
    atlas_lib.mkdir()
    (atlas_lib / "atlas_utils.py").write_text(
        "atlas_version = '1.0'\ndef atlas_util_func():\n    pass\n"
    )

    # Nested atlas_ directory
    nested = base_dir / "lib" / "atlas_module"
    nested.mkdir(parents=True)
    (nested / "atlas_core.py").write_text(
        "class atlas_codec:\n    atlas_mode = 'production'\n"
    )

    # Directories that should be excluded
    vendor_dir = base_dir / "vendor" / "atlas_vendor"
    vendor_dir.mkdir(parents=True)
    (vendor_dir / "atlas_vendor_lib.py").write_text(
        "ATLAS_VENDOR_KEY = 'should_stay'\n"
    )

    node_modules_dir = base_dir / "node_modules" / "atlas_pkg"
    node_modules_dir.mkdir(parents=True)
    (node_modules_dir / "atlas_pkg.js").write_text("const ATLAS_TOKEN = 'excluded';")

    git_dir = base_dir / ".git" / "atlas_hooks"
    git_dir.mkdir(parents=True)
    (git_dir / "atlas_hook.sh").write_text("echo 'ATLAS_HOOK_EXCLUDE'")

    # Clean file with no atlas_ references (should stay intact)
    (base_dir / "neutral.txt").write_text("nothing to see here\njust neutral content\n")


class TestRefactorDryRun:
    """Test dry-run mode: reports changes but does not modify anything."""

    def test_dry_run_reports_but_does_not_modify(self):
        """Dry-run should output planned changes but leave files untouched."""
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            _create_test_fixture(base)

            # Snapshot file contents before dry-run
            files_before = {}
            for root, dirs, files in os.walk(base):
                for f in files:
                    fp = Path(root) / f
                    files_before[str(fp)] = fp.read_text()

            result = _run_refactor("--target-path", str(base), "--dry-run", cwd=tmp)

            assert result.returncode == 0, f"dry-run failed: {result.stderr}"
            stdout = result.stdout

            # Should report planned actions
            assert (
                "DRY-RUN" in stdout.upper()
                or "would" in stdout.lower()
                or "dry" in stdout.lower()
                or len(stdout) > 0
            )

            # Verify NO files were actually modified
            for fp_str, before_content in files_before.items():
                after_content = Path(fp_str).read_text()
                assert after_content == before_content, (
                    f"Dry-run modified {fp_str}!\n"
                    f"Before: {before_content!r}\n"
                    f"After:  {after_content!r}"
                )

            # Verify directory names unchanged
            dirs_before = set()
            for root, dirs, _ in os.walk(base):
                for d in dirs:
                    dirs_before.add(Path(root) / d)
            dirs_after = set()
            for root, dirs, _ in os.walk(base):
                for d in dirs:
                    dirs_after.add(Path(root) / d)
            assert dirs_before == dirs_after, "Dry-run modified directory names!"

    def test_dry_run_output_describes_changes(self):
        """Dry-run output should mention what would change."""
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            _create_test_fixture(base)

            result = _run_refactor("--target-path", str(base), "--dry-run", cwd=tmp)
            assert result.returncode == 0

            stdout = result.stdout
            # Should mention atlas_ somewhere (what it found)
            assert "atlas_" in stdout.lower() or "aura_" in stdout.lower(), (
                f"Dry-run output should reference atlas_/aura_: {stdout[:500]}"
            )


class TestRefactorRealRename:
    """Test real rename mode: replaces all atlas_ -> aura_."""

    def test_real_rename_replaces_all_atlas_with_aura_in_contents(self):
        """Real rename replaces all atlas_ with aura_ in file contents."""
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            _create_test_fixture(base)

            result = _run_refactor("--target-path", str(base), cwd=tmp)
            assert result.returncode == 0, f"refactor failed: {result.stderr}"

            # Check main.py content
            content = (base / "main.py").read_text()
            assert "atlas_config" not in content
            assert "atlas_secret" not in content
            assert "atlas_init" not in content
            assert "aura_config" in content
            assert "aura_secret" in content
            assert "aura_init" in content

            # Check service.go content
            content = (base / "service.go").read_text()
            assert "atlas_service" not in content
            assert "atlas_host_default" not in content
            assert "aura_service" in content
            assert "aura_host_default" in content
            # "AtlasClient" (PascalCase, no underscore) is NOT replaced by literal atlas_→aura_
            assert "AtlasClient" in content

    def test_file_name_renames(self):
        """File names containing atlas_ should be renamed to aura_."""
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            _create_test_fixture(base)

            result = _run_refactor("--target-path", str(base), cwd=tmp)
            assert result.returncode == 0

            # Files that should be renamed
            assert not (base / "atlas_config.py").exists(), (
                "atlas_config.py should be renamed"
            )
            assert (base / "aura_config.py").exists(), "aura_config.py should exist"
            assert not (base / "atlas_worker.go").exists(), (
                "atlas_worker.go should be renamed"
            )
            assert (base / "aura_worker.go").exists(), "aura_worker.go should exist"

            # Clean file unchanged
            assert (base / "neutral.txt").exists()

    def test_directory_renames(self):
        """Directory names containing atlas_ should be renamed to aura_."""
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            _create_test_fixture(base)

            result = _run_refactor("--target-path", str(base), cwd=tmp)
            assert result.returncode == 0

            # atlas_lib/ -> aura_lib/
            assert not (base / "atlas_lib").exists(), "atlas_lib/ should be renamed"
            assert (base / "aura_lib").exists(), "aura_lib/ should exist"
            assert (base / "aura_lib" / "aura_utils.py").exists()

            # lib/atlas_module/ -> lib/aura_module/
            assert not (base / "lib" / "atlas_module").exists()
            assert (base / "lib" / "aura_module").exists()
            assert (base / "lib" / "aura_module" / "aura_core.py").exists()

            # Content in renamed directories also transformed
            content = (base / "lib" / "aura_module" / "aura_core.py").read_text()
            assert "atlas_" not in content, f"Content still has atlas_: {content!r}"
            assert "aura_codec" in content
            assert "aura_mode" in content

    def test_exclusion_patterns(self):
        """vendor/, node_modules/, .git/ should be skipped entirely."""
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            _create_test_fixture(base)

            result = _run_refactor("--target-path", str(base), cwd=tmp)
            assert result.returncode == 0

            # vendor/ should be untouched
            vendor_file = base / "vendor" / "atlas_vendor" / "atlas_vendor_lib.py"
            assert vendor_file.exists(), "vendor/ should not be touched"
            content = vendor_file.read_text()
            assert "ATLAS_VENDOR" in content, "vendor/ content should remain unchanged"

            vendor_dir = base / "vendor" / "atlas_vendor"
            assert vendor_dir.exists(), "vendor/atlas_vendor dir name should remain"

            # node_modules/ should be untouched
            nm_file = base / "node_modules" / "atlas_pkg" / "atlas_pkg.js"
            assert nm_file.exists(), "node_modules/ should not be touched"
            assert "ATLAS_TOKEN" in nm_file.read_text()

            # .git/ should be untouched
            git_file = base / ".git" / "atlas_hooks" / "atlas_hook.sh"
            assert git_file.exists(), ".git/ should not be touched"
            assert "ATLAS_HOOK_EXCLUDE" in git_file.read_text()

    def test_custom_exclude_pattern(self):
        """Custom --exclude patterns should also be honored."""
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            _create_test_fixture(base)

            # Add a custom directory to exclude
            custom_dir = base / "custom_excluded" / "atlas_custom"
            custom_dir.mkdir(parents=True)
            (custom_dir / "atlas_custom.py").write_text("ATLAS_CUSTOM = 'keep'")

            result = _run_refactor(
                "--target-path",
                str(base),
                "--exclude",
                "custom_excluded",
                cwd=tmp,
            )
            assert result.returncode == 0

            # custom_excluded should be untouched
            custom_file = base / "custom_excluded" / "atlas_custom" / "atlas_custom.py"
            assert custom_file.exists(), "custom_excluded should be untouched"
            assert "ATLAS_CUSTOM" in custom_file.read_text()

            # Other files should still be renamed
            assert not (base / "atlas_config.py").exists()


class TestIdentityCheck:
    """Test identity-check.py: verifies zero atlas_ references remain."""

    def test_identity_check_detects_remaining(self):
        """identity-check should exit non-zero when atlas_ references remain."""
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            _create_test_fixture(base)

            # Don't run refactor — atlas_ should remain
            result = _run_identity_check("--target-path", str(base), cwd=tmp)
            assert result.returncode != 0, (
                f"identity-check should fail when atlas_ remains, "
                f"got exit={result.returncode}, stdout={result.stdout[:300]}"
            )

    def test_identity_check_passes_clean(self):
        """identity-check should exit 0 when NO atlas_ references remain."""
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            _create_test_fixture(base)

            # Run refactor first
            ref_result = _run_refactor("--target-path", str(base), cwd=tmp)
            assert ref_result.returncode == 0

            # Now identity-check should pass
            result = _run_identity_check("--target-path", str(base), cwd=tmp)
            assert result.returncode == 0, (
                f"identity-check should pass after refactor, "
                f"got exit={result.returncode}, stderr={result.stderr[:300]}"
            )
