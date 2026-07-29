#!/usr/bin/env bash
set -euo pipefail

# =============================================================================
# deploy-gcr.sh — Master Cloud Run deploy script
# Deploys all 8 services to aissc-core-engine-self-dep in us-central1
# =============================================================================

PROJECT="aissc-core-engine-self-dep"
REGION="us-central1"
SERVICE_ACCOUNT="core-engine-worker@${PROJECT}.iam.gserviceaccount.com"

# Sizing constants (free-tier compliant)
CPU="1"
MEMORY="512Mi"
MIN_INSTANCES="0"
MAX_INSTANCES="1"

# ---------------------------------------------------------------------------
# Stage shared files into a service directory before building.
# Some services need files from outside their own directory (src/ledger.py,
# memory_client.py, etc.). Cloud Run source deploy uses the service dir as
# the Docker build context, so we pre-copy shared deps and remove afterward.
# ---------------------------------------------------------------------------
stage_shared_deps() {
    local target_dir="$1"
    shift
    for src_path in "$@"; do
        local dest="${target_dir}/$(basename "${src_path}")"
        if [[ -f "${src_path}" ]]; then
            cp "${src_path}" "${dest}"
        elif [[ -d "${src_path}" ]]; then
            cp -r "${src_path}" "${dest}"
        fi
    done
}

cleanup_shared_deps() {
    local target_dir="$1"
    shift
    for src_path in "$@"; do
        local dest="${target_dir}/$(basename "${src_path}")"
        rm -rf "${dest}"
    done
}

# ---------------------------------------------------------------------------
# Helper: deploy an internal-only service (ingress=internal, default-private auth)
# ---------------------------------------------------------------------------
deploy_internal() {
    local service_name="$1"
    local source_dir="$2"
    local port="${3:-8080}"

    echo ""
    echo "=============================================================================="
    echo "  DEPLOYING: ${service_name}  (source: ${source_dir}, port: ${port})"
    echo "=============================================================================="

    gcloud run deploy "${service_name}" \
        --source "${source_dir}" \
        --region "${REGION}" \
        --project "${PROJECT}" \
        --ingress internal \
        --port "${port}" \
        --cpu "${CPU}" \
        --memory "${MEMORY}" \
        --min-instances "${MIN_INSTANCES}" \
        --max-instances "${MAX_INSTANCES}" \
        --service-account "${SERVICE_ACCOUNT}" \
        --quiet

    echo ">>> ${service_name} deployed successfully."
}

# ---------------------------------------------------------------------------
# Enable required APIs (idempotent)
# ---------------------------------------------------------------------------
echo "=== Enabling Cloud Run + Cloud Build APIs ==="
gcloud services enable run.googleapis.com cloudbuild.googleapis.com \
    --project "${PROJECT}" --quiet

# ===========================================================================
# Phase 1: Core C-P-A services (Track A + Track B)
# ===========================================================================
echo ""
echo "##############################################################################"
echo "#  PHASE 1: Core C-P-A Services"
echo "##############################################################################"

deploy_internal "track-a-control-loop" "./track-a" "8080"
deploy_internal "track-b-actuator"   "./track-b" "8081"

# ===========================================================================
# Phase 2: Executive Quartet (sheryl, aura, malory, krieger)
# ===========================================================================
echo ""
echo "##############################################################################"
echo "#  PHASE 2: Executive Quartet"
echo "##############################################################################"

# Stage shared files for sheryl-agent (needs memory_client.py + src/ package)
stage_shared_deps "./executive-quartet/sheryl" \
    "./executive-quartet/memory_client.py" \
    "./src"
deploy_internal "sheryl-agent" "./executive-quartet/sheryl" "8083"
cleanup_shared_deps "./executive-quartet/sheryl" \
    "./executive-quartet/memory_client.py" \
    "./src"

# Stage shared file for aura-agent (needs memory_client.py)
stage_shared_deps "./executive-quartet/aura" \
    "./executive-quartet/memory_client.py"
deploy_internal "aura-agent"   "./executive-quartet/aura" "8084"
cleanup_shared_deps "./executive-quartet/aura" \
    "./executive-quartet/memory_client.py"

# Stage shared file for malory-agent (needs memory_client.py)
stage_shared_deps "./executive-quartet/malory" \
    "./executive-quartet/memory_client.py"
deploy_internal "malory-agent" "./executive-quartet/malory" "8085"
cleanup_shared_deps "./executive-quartet/malory" \
    "./executive-quartet/memory_client.py"

# Stage shared file for krieger-agent (needs memory_client.py)
stage_shared_deps "./executive-quartet/krieger" \
    "./executive-quartet/memory_client.py"
deploy_internal "krieger-agent" "./executive-quartet/krieger" "8086"
cleanup_shared_deps "./executive-quartet/krieger" \
    "./executive-quartet/memory_client.py"

# ===========================================================================
# Phase 3: Self-Remediation
# ===========================================================================
echo ""
echo "##############################################################################"
echo "#  PHASE 3: Self-Remediation"
echo "##############################################################################"

# Stage shared files for self-remediation (needs full src/ directory for ledger)
stage_shared_deps "./self-remediation" "./src"
deploy_internal "self-remediation" "./self-remediation" "8087"
cleanup_shared_deps "./self-remediation" "./src"

# ===========================================================================
# Phase 4: Telegram Bridge (PUBLIC — only externally-accessible service)
# ===========================================================================
echo ""
echo "##############################################################################"
echo "#  PHASE 4: Telegram Bridge (PUBLIC)"
echo "##############################################################################"

echo ""
echo "=============================================================================="
echo "  DEPLOYING: telegram-bridge  (source: ./telegram-bridge, port: 8088)  [PUBLIC]"
echo "=============================================================================="

gcloud run deploy "telegram-bridge" \
    --source "./telegram-bridge" \
    --port "8088" \
    --region "${REGION}" \
    --project "${PROJECT}" \
    --allow-unauthenticated \
    --cpu "${CPU}" \
    --memory "${MEMORY}" \
    --min-instances "${MIN_INSTANCES}" \
    --max-instances "${MAX_INSTANCES}" \
    --service-account "${SERVICE_ACCOUNT}" \
    --quiet

echo ">>> telegram-bridge deployed successfully."

# ===========================================================================
# Summary
# ===========================================================================
echo ""
echo "##############################################################################"
echo "#  DEPLOYMENT SUMMARY"
echo "##############################################################################"
echo ""

gcloud run services list \
    --project "${PROJECT}" \
    --region "${REGION}" \
    --format='table(name, status.address.url, status.conditions[0].status:label=READY)'

echo ""
echo "All 8 services deployed to ${PROJECT} (${REGION})."
echo "Only telegram-bridge is publicly accessible."
