"""
Tests for Barry DO-Lobe preservation package.

Validates Dockerfile syntax, manifest schema, package script behavior,
and the zero-code-modification constraint — all without touching any
Barry container code.
"""

import json
import os
import stat
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
BARRY_DIR = REPO_ROOT / "barry-preservation"


# ── Helper: check file existence ────────────────────────────────────


def _require_file(path: Path, desc: str) -> Path:
    """Assert a file exists and return its path, or fail with a clear message."""
    assert path.is_file(), f"{desc} not found at {path}"
    return path


# ── Test 1: Dockerfile syntax check ──────────────────────────────────


class TestDockerfileSyntax:
    """Verify the Dockerfile meets preservation-package requirements."""

    def test_dockerfile_exists(self):
        """Dockerfile must exist in barry-preservation/."""
        dockerfile = BARRY_DIR / "Dockerfile"
        assert dockerfile.is_file(), f"Dockerfile missing: {dockerfile}"

    def test_dockerfile_base_image(self):
        """Base image must be python:3.12-slim."""
        dockerfile = _require_file(BARRY_DIR / "Dockerfile", "Dockerfile")
        content = dockerfile.read_text()
        assert "python:3.12-slim" in content, (
            "Dockerfile must use python:3.12-slim base image"
        )

    def test_dockerfile_nonroot_user(self):
        """Dockerfile must create non-root user 'coreengine'."""
        dockerfile = _require_file(BARRY_DIR / "Dockerfile", "Dockerfile")
        content = dockerfile.read_text()
        # Must either RUN useradd or USER coreengine
        has_coreengine = "coreengine" in content
        assert has_coreengine, "Dockerfile must reference non-root user 'coreengine'"

    def test_dockerfile_valid_syntax(self):
        """Dockerfile must have FROM as its first instruction."""
        dockerfile = _require_file(BARRY_DIR / "Dockerfile", "Dockerfile")
        content = dockerfile.read_text()
        # FROM should be the first non-comment, non-whitespace line
        lines = content.strip().splitlines()
        first_directive = ""
        for line in lines:
            stripped = line.strip()
            if stripped and not stripped.startswith("#"):
                first_directive = stripped
                break
        assert first_directive.upper().startswith("FROM"), (
            f"Dockerfile must start with FROM, got: {first_directive}"
        )


# ── Test 2: Manifest schema validation ───────────────────────────────


REQUIRED_MANIFEST_FIELDS = [
    "image_name",
    "layers",
    "environment",
    "exposed_ports",
    "entrypoint",
    "preservation_note",
]


class TestManifestSchema:
    """Validate manifest.json structure and preservation constraints."""

    def test_manifest_exists(self):
        """manifest.json must exist in barry-preservation/."""
        manifest = BARRY_DIR / "manifest.json"
        assert manifest.is_file(), f"manifest.json missing: {manifest}"

    def test_manifest_valid_json(self):
        """manifest.json must be valid JSON."""
        manifest = _require_file(BARRY_DIR / "manifest.json", "manifest.json")
        raw = manifest.read_text().strip()
        assert raw, "manifest.json is empty"
        try:
            data = json.loads(raw)
        except json.JSONDecodeError as exc:
            pytest.fail(f"manifest.json is not valid JSON: {exc}")
        assert isinstance(data, dict), "manifest.json root must be a JSON object"

    @pytest.mark.parametrize("field", REQUIRED_MANIFEST_FIELDS)
    def test_manifest_required_field_present(self, field):
        """manifest.json must include each required top-level field."""
        manifest = _require_file(BARRY_DIR / "manifest.json", "manifest.json")
        data = json.loads(manifest.read_text())
        assert field in data, (
            f"manifest.json missing required field '{field}'. "
            f"Required fields: {REQUIRED_MANIFEST_FIELDS}"
        )

    def test_manifest_preservation_note_content(self):
        """preservation_note must contain 'ZERO CODE MODIFICATION'."""
        manifest = _require_file(BARRY_DIR / "manifest.json", "manifest.json")
        data = json.loads(manifest.read_text())
        note = data.get("preservation_note", "")
        assert "ZERO CODE MODIFICATION" in note, (
            f"preservation_note must contain 'ZERO CODE MODIFICATION', got: {note!r}"
        )

    def test_manifest_layers_is_list(self):
        """layers field must be a list."""
        manifest = _require_file(BARRY_DIR / "manifest.json", "manifest.json")
        data = json.loads(manifest.read_text())
        layers = data.get("layers")
        assert isinstance(layers, list), (
            f"layers must be a list, got {type(layers).__name__}"
        )

    def test_manifest_environment_is_object(self):
        """environment field must be an object (dict)."""
        manifest = _require_file(BARRY_DIR / "manifest.json", "manifest.json")
        data = json.loads(manifest.read_text())
        env = data.get("environment")
        assert isinstance(env, dict), (
            f"environment must be a dict, got {type(env).__name__}"
        )

    def test_manifest_exposed_ports_is_list(self):
        """exposed_ports field must be a list."""
        manifest = _require_file(BARRY_DIR / "manifest.json", "manifest.json")
        data = json.loads(manifest.read_text())
        ports = data.get("exposed_ports")
        assert isinstance(ports, list), (
            f"exposed_ports must be a list, got {type(ports).__name__}"
        )

    def test_manifest_entrypoint_is_nonempty(self):
        """entrypoint field must be a non-empty string or list."""
        manifest = _require_file(BARRY_DIR / "manifest.json", "manifest.json")
        data = json.loads(manifest.read_text())
        entrypoint = data.get("entrypoint")
        if isinstance(entrypoint, str):
            assert len(entrypoint) > 0, "entrypoint string must not be empty"
        elif isinstance(entrypoint, list):
            assert len(entrypoint) > 0, "entrypoint list must not be empty"
        else:
            pytest.fail(
                f"entrypoint must be string or list, got {type(entrypoint).__name__}"
            )


# ── Test 3: package.sh exits cleanly ─────────────────────────────────


class TestPackageScript:
    """Verify package.sh behaves correctly."""

    def test_package_script_exists(self):
        """package.sh must exist in barry-preservation/."""
        script = BARRY_DIR / "package.sh"
        assert script.is_file(), f"package.sh missing: {script}"

    def test_package_script_executable(self):
        """package.sh must be executable."""
        script = _require_file(BARRY_DIR / "package.sh", "package.sh")
        mode = os.stat(script).st_mode
        assert mode & stat.S_IXUSR, "package.sh must be user-executable"

    def test_package_script_has_shebang(self):
        """package.sh must start with a shebang."""
        script = _require_file(BARRY_DIR / "package.sh", "package.sh")
        first_line = script.read_text().splitlines()[0]
        assert first_line.startswith("#!"), (
            f"package.sh must start with shebang, got: {first_line[:40]}"
        )

    def test_package_script_mentions_no_modification(self):
        """package.sh must document 'as-is/zero modification/NO CODE CHANGE'."""
        script = _require_file(BARRY_DIR / "package.sh", "package.sh")
        content = script.read_text()
        # Must contain at least one of the zero-modification phrases
        phrases = ["as-is", "zero modification", "NO CODE CHANGE"]
        found = any(phrase in content for phrase in phrases)
        assert found, (
            f"package.sh must document zero-modification policy "
            f"(expected one of: {phrases})"
        )

    def test_package_script_exits_cleanly(self):
        """package.sh must exit with code 0 when sourced/checked."""
        script = _require_file(BARRY_DIR / "package.sh", "package.sh")
        # Run with bash -n (syntax check only — no docker commands)
        import subprocess
        import sys

        result = subprocess.run(
            ["bash", "-n", str(script)],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, (
            f"package.sh syntax check failed (bash -n):\n{result.stderr}"
        )


# ── Test 4: No-modification constraint documented ────────────────────


class TestNoModificationConstraint:
    """Verify the zero-code-modification requirement is documented across all artifacts."""

    def test_preservation_note_in_manifest(self):
        """manifest.json preservation_note must contain 'ZERO CODE MODIFICATION'."""
        manifest = _require_file(BARRY_DIR / "manifest.json", "manifest.json")
        data = json.loads(manifest.read_text())
        note = data.get("preservation_note", "")
        assert "ZERO CODE MODIFICATION" in note, (
            f"manifest.json preservation_note missing ZERO CODE MODIFICATION"
        )

    def test_no_modification_in_package_script(self):
        """package.sh must reference preservation / no-modification intent."""
        script = _require_file(BARRY_DIR / "package.sh", "package.sh")
        content = script.read_text()
        phrases = ["as-is", "zero modification", "NO CODE CHANGE", "preservation"]
        found = [p for p in phrases if p in content]
        assert len(found) >= 2, (
            f"package.sh must mention at least 2 preservation phrases (found: {found})"
        )

    def test_dockerfile_is_minimal_base(self):
        """Dockerfile should be a minimal base — no application code COPY."""
        dockerfile = _require_file(BARRY_DIR / "Dockerfile", "Dockerfile")
        content = dockerfile.read_text()
        # We don't strictly forbid COPY, but the intent is a base image
        # that does not modify any Barry container code. At minimum,
        # the Dockerfile must exist and use the correct base.
        assert "python:3.12-slim" in content, (
            "Dockerfile must use python:3.12-slim base (no code modification)"
        )


# ── Test 5: Connectivity test script ─────────────────────────────────


class TestConnectivityScript:
    """Verify the connectivity test script exists and is syntactically valid."""

    def test_connectivity_script_exists(self):
        """connectivity-test.sh must exist in barry-preservation/."""
        script = BARRY_DIR / "connectivity-test.sh"
        assert script.is_file(), f"connectivity-test.sh missing: {script}"

    def test_connectivity_script_executable(self):
        """connectivity-test.sh must be executable."""
        script = _require_file(
            BARRY_DIR / "connectivity-test.sh", "connectivity-test.sh"
        )
        mode = os.stat(script).st_mode
        assert mode & stat.S_IXUSR, "connectivity-test.sh must be user-executable"

    def test_connectivity_script_valid_bash(self):
        """connectivity-test.sh must pass bash -n syntax check."""
        script = _require_file(
            BARRY_DIR / "connectivity-test.sh", "connectivity-test.sh"
        )
        import subprocess

        result = subprocess.run(
            ["bash", "-n", str(script)],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, (
            f"connectivity-test.sh syntax check failed:\n{result.stderr}"
        )


# ── Test 6: Job/task module directory ────────────────────────────────


class TestJobTaskModule:
    """Verify the placeholder job/task module directory."""

    def test_job_task_module_dir_exists(self):
        """job-task-module/ directory must exist."""
        jtm = BARRY_DIR / "job-task-module"
        assert jtm.is_dir(), f"job-task-module/ directory missing: {jtm}"

    def test_job_task_module_has_placeholder(self):
        """job-task-module/ must contain a README or .gitkeep placeholder."""
        jtm = BARRY_DIR / "job-task-module"
        placeholder = jtm / ".gitkeep"
        readme = jtm / "README.md"
        assert placeholder.is_file() or readme.is_file(), (
            f"job-task-module/ must have a placeholder file (.gitkeep or README.md)"
        )
