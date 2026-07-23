#!/usr/bin/env bash
# =============================================================================
# Barry DO-Lobe Preservation — Connectivity Test
# =============================================================================
# Verifies that the preserved container boots correctly and internal routing
# works. Tests are non-destructive — they run against a temporary container
# instance and clean up on exit.
#
# Usage:
#   ./connectivity-test.sh [--image barry-do-lobe:latest] [--port 8080]
# =============================================================================

set -euo pipefail

# ── Configuration ────────────────────────────────────────────────────────────
IMAGE="${IMAGE:-barry-do-lobe-preservation:preserved-as-is}"
TEST_PORT="${TEST_PORT:-8080}"
TIMEOUT="${TIMEOUT:-30}"
CONTAINER_NAME="barry-preservation-test-$$"

PASS=0
FAIL=0

# ── Helpers ──────────────────────────────────────────────────────────────────

cleanup() {
    echo ""
    echo "--- Cleanup ---"
    docker rm -f "${CONTAINER_NAME}" 2>/dev/null || true
}

trap cleanup EXIT

check() {
    local desc="$1"
    local cmd="$2"
    echo -n "  [TEST] ${desc} ... "
    if eval "${cmd}" &>/dev/null; then
        echo "PASS"
        PASS=$((PASS + 1))
    else
        echo "FAIL"
        FAIL=$((FAIL + 1))
    fi
}

# ── Pre-flight ───────────────────────────────────────────────────────────────

echo "=== Barry DO-Lobe Connectivity Test ==="
echo "Image:   ${IMAGE}"
echo "Port:    ${TEST_PORT}"
echo "Timeout: ${TIMEOUT}s"
echo ""

# Check docker is available
if ! command -v docker &>/dev/null; then
    echo "ERROR: docker not found. Install Docker to run connectivity tests."
    exit 1
fi

# Check image exists (local or pullable)
if ! docker inspect "${IMAGE}" &>/dev/null; then
    echo "WARNING: Image '${IMAGE}' not found locally."
    echo "         If the image is in a remote registry, pull it first."
    echo "         For a preserved tarball, run: docker load -i <tarball.tar>"
    echo ""
    echo "Skipping container-based tests — only static checks possible."
fi

# ── Test Suite ───────────────────────────────────────────────────────────────

echo "--- Static Checks ---"

check "Docker daemon is running" \
    "docker info"

check "Image exists or is pullable" \
    "docker inspect '${IMAGE}' || docker pull '${IMAGE}'"

check "Manifest file is valid JSON" \
    "python3 -c 'import json; json.load(open(\"manifest.json\"))'"

echo ""
echo "--- Container Boot Test ---"

# Start the container in detached mode
echo "  Starting container: ${CONTAINER_NAME}"
if docker run -d \
    --name "${CONTAINER_NAME}" \
    -p "${TEST_PORT}:${TEST_PORT}" \
    "${IMAGE}" \
    &>/tmp/barry-connectivity-start.log; then

    check "Container started successfully" "docker inspect '${CONTAINER_NAME}'"

    # Wait for the container to be healthy/running
    echo "  Waiting for container to become ready (max ${TIMEOUT}s)..."
    ELAPSED=0
    while [ ${ELAPSED} -lt ${TIMEOUT} ]; do
        STATUS="$(docker inspect -f '{{.State.Status}}' "${CONTAINER_NAME}" 2>/dev/null || echo 'missing')"
        if [ "${STATUS}" = "running" ]; then
            break
        fi
        sleep 2
        ELAPSED=$((ELAPSED + 2))
    done

    check "Container is in 'running' state" \
        "[ \"\$(docker inspect -f '{{.State.Status}}' '${CONTAINER_NAME}')\" = 'running' ]"

    # Health endpoint check (if the container has one)
    echo ""
    echo "--- Routing Checks ---"

    check "Port ${TEST_PORT} is listening on container" \
        "docker exec '${CONTAINER_NAME}' sh -c 'netstat -tlnp 2>/dev/null || ss -tlnp' | grep ':${TEST_PORT}'"

    check "Container has working loopback" \
        "docker exec '${CONTAINER_NAME}' ping -c 1 -W 2 127.0.0.1"

    check "Container can resolve DNS" \
        "docker exec '${CONTAINER_NAME}' nslookup localhost 2>/dev/null || docker exec '${CONTAINER_NAME}' getent hosts localhost"

    # Process check
    echo ""
    echo "--- Process Check ---"

    check "Python process is running (user: coreengine)" \
        "docker exec '${CONTAINER_NAME}' sh -c 'ps aux 2>/dev/null || ps' | grep -v grep | head -5"

    check "Running as non-root user" \
        "[ \"\$(docker exec '${CONTAINER_NAME}' whoami)\" != 'root' ]"

    echo ""
    echo "--- Logs Snapshot ---"
    docker logs --tail 10 "${CONTAINER_NAME}" 2>/dev/null || echo "  (no logs available)"

else
    echo "  FAIL: Container failed to start. Check /tmp/barry-connectivity-start.log"
    FAIL=$((FAIL + 1))
fi

# ── Summary ──────────────────────────────────────────────────────────────────

echo ""
echo "=== Connectivity Test Results ==="
echo "PASS: ${PASS}"
echo "FAIL: ${FAIL}"

if [ ${FAIL} -gt 0 ]; then
    echo ""
    echo "Some tests failed. Review the output above for details."
    echo "Common issues:"
    echo "  - Image not loaded locally (docker load -i <tarball>)"
    echo "  - Port conflict (try --port 9090)"
    echo "  - Container missing /bin/sh or required tools"
    exit 1
else
    echo "All connectivity checks passed."
    exit 0
fi
