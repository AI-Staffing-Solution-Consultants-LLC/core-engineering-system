#!/usr/bin/env bash
# =============================================================================
# Barry DO-Lobe Preservation — Package Script
# =============================================================================
# POLICY: ZERO CODE MODIFICATION / AS-IS PRESERVATION / NO CODE CHANGE
#
# This script documents the process of pulling the Barry DO-Lobe container,
# exporting it as a tarball, and generating a preservation manifest.
#
# It does NOT modify any Barry container code. It captures the container
# in its current running state for migration/replication purposes.
#
# Usage:
#   ./package.sh [--dry-run] [--output-dir ./exports]
# =============================================================================

set -euo pipefail

# ── Configuration ────────────────────────────────────────────────────────────
OUTPUT_DIR="${OUTPUT_DIR:-./exports}"
DRY_RUN="${DRY_RUN:-false}"
TIMESTAMP="$(date -u +%Y-%m-%dT%H:%M:%SZ)"

# Container identification — set these before running
# WARNING: Do NOT hardcode live DO credentials here.
# Use environment variables or a .env file (gitignored).
DO_REGISTRY="${DO_REGISTRY:-}"
CONTAINER_NAME="${CONTAINER_NAME:-barry-do-lobe}"
CONTAINER_TAG="${CONTAINER_TAG:-latest}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MANIFEST_FILE="${SCRIPT_DIR}/manifest.json"

# ── Safety checks ────────────────────────────────────────────────────────────

echo "=== Barry DO-Lobe Preservation Package ==="
echo "Timestamp: ${TIMESTAMP}"
echo "Policy: ZERO CODE MODIFICATION / AS-IS PRESERVATION"
echo ""

if [ "${DRY_RUN}" = "true" ]; then
    echo "[DRY RUN] Would perform preservation steps without making changes."
fi

# ── Step 1: Verify manifest exists ───────────────────────────────────────────
if [ ! -f "${MANIFEST_FILE}" ]; then
    echo "ERROR: manifest.json not found at ${MANIFEST_FILE}"
    echo "The manifest records container metadata. Create it before packaging."
    exit 1
fi

echo "[1/4] Manifest verified: ${MANIFEST_FILE}"
IMAGE_NAME="$(python3 -c "import json; print(json.load(open('${MANIFEST_FILE}'))['image_name'])" 2>/dev/null || echo "barry-do-lobe-preservation")"
echo "       Image name from manifest: ${IMAGE_NAME}"

# ── Step 2: Pull container from DO registry (if registry configured) ─────────
echo "[2/4] Container pull step..."

if [ -n "${DO_REGISTRY}" ]; then
    FULL_IMAGE="${DO_REGISTRY}/${CONTAINER_NAME}:${CONTAINER_TAG}"
    echo "       Target: ${FULL_IMAGE}"
    if [ "${DRY_RUN}" != "true" ]; then
        echo "       Pulling container from DigitalOcean registry..."
        docker pull "${FULL_IMAGE}" || {
            echo "WARNING: docker pull failed. Is the registry reachable?"
            echo "         Proceeding with local-only preservation."
        }
    else
        echo "       [DRY RUN] Would execute: docker pull ${FULL_IMAGE}"
    fi
else
    echo "       DO_REGISTRY not set — skipping remote pull."
    echo "       To pull from DO, set: export DO_REGISTRY=registry.digitalocean.com/your-registry"
    echo ""
    echo "       Using local container state instead."
fi

# ── Step 3: Export container as tarball ──────────────────────────────────────
echo "[3/4] Exporting container as tarball..."

mkdir -p "${OUTPUT_DIR}"
TARBALL="${OUTPUT_DIR}/${CONTAINER_NAME}-${CONTAINER_TAG}-$(date -u +%Y%m%d-%H%M%S).tar"

if [ "${DRY_RUN}" != "true" ]; then
    # Check if container exists locally
    if docker inspect "${CONTAINER_NAME}:${CONTAINER_TAG}" &>/dev/null; then
        echo "       Saving: ${CONTAINER_NAME}:${CONTAINER_TAG} → ${TARBALL}"
        docker save -o "${TARBALL}" "${CONTAINER_NAME}:${CONTAINER_TAG}"
        echo "       Tarball size: $(du -h "${TARBALL}" | cut -f1)"
        echo "       SHA256: $(sha256sum "${TARBALL}" | cut -d' ' -f1)"
    elif [ -n "${DO_REGISTRY}" ]; then
        FULL_IMAGE="${DO_REGISTRY}/${CONTAINER_NAME}:${CONTAINER_TAG}"
        echo "       Saving remote image: ${FULL_IMAGE} → ${TARBALL}"
        docker save -o "${TARBALL}" "${FULL_IMAGE}"
        echo "       Tarball size: $(du -h "${TARBALL}" | cut -f1)"
        echo "       SHA256: $(sha256sum "${TARBALL}" | cut -d' ' -f1)"
    else
        echo "       WARNING: No local or remote container found to export."
        echo "       The tarball was not created."
    fi
else
    echo "       [DRY RUN] Would export container to: ${TARBALL}"
fi

# ── Step 4: Save manifest alongside tarball ──────────────────────────────────
echo "[4/4] Saving preservation manifest..."

MANIFEST_COPY="${OUTPUT_DIR}/manifest-$(date -u +%Y%m%d-%H%M%S).json"
if [ "${DRY_RUN}" != "true" ]; then
    cp "${MANIFEST_FILE}" "${MANIFEST_COPY}"
    echo "       Manifest saved to: ${MANIFEST_COPY}"
else
    echo "       [DRY RUN] Would copy manifest to: ${MANIFEST_COPY}"
fi

# ── Summary ──────────────────────────────────────────────────────────────────
echo ""
echo "=== Preservation Complete ==="
echo "Policy: ZERO CODE MODIFICATION / AS-IS PRESERVATION / NO CODE CHANGE"
echo "Output directory: ${OUTPUT_DIR}"
echo ""
echo "Next steps:"
echo "  1. Verify tarball: tar -tf ${TARBALL} | head"
echo "  2. Load on target: docker load -i ${TARBALL}"
echo "  3. Run connectivity-test.sh to verify the preserved container boots"
echo "  4. Compare manifest.json with loaded image: docker inspect ${IMAGE_NAME}"
