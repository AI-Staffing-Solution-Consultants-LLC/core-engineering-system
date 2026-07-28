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
# Helper: deploy an internal-only service (ingress=internal, default-private auth)
# ---------------------------------------------------------------------------
deploy_internal() {
    local service_name="$1"
    local source_dir="$2"

    echo ""
    echo "=============================================================================="
    echo "  DEPLOYING: ${service_name}  (source: ${source_dir})"
    echo "=============================================================================="

    gcloud run deploy "${service_name}" \
        --source "${source_dir}" \
        --region "${REGION}" \
        --project "${PROJECT}" \
        --ingress internal \
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

deploy_internal "track-a-control-loop" "./track-a"
deploy_internal "track-b-actuator"   "./track-b"

# ===========================================================================
# Phase 2: Executive Quartet (sheryl, aura, malory, krieger)
# ===========================================================================
echo ""
echo "##############################################################################"
echo "#  PHASE 2: Executive Quartet"
echo "##############################################################################"

deploy_internal "sheryl-agent" "./executive-quartet/sheryl"
deploy_internal "aura-agent"   "./executive-quartet/aura"
deploy_internal "malory-agent" "./executive-quartet/malory"
deploy_internal "krieger-agent" "./executive-quartet/krieger"

# ===========================================================================
# Phase 3: Self-Remediation
# ===========================================================================
echo ""
echo "##############################################################################"
echo "#  PHASE 3: Self-Remediation"
echo "##############################################################################"

deploy_internal "self-remediation" "./self-remediation"

# ===========================================================================
# Phase 4: Telegram Bridge (PUBLIC — only externally-accessible service)
# ===========================================================================
echo ""
echo "##############################################################################"
echo "#  PHASE 4: Telegram Bridge (PUBLIC)"
echo "##############################################################################"

echo ""
echo "=============================================================================="
echo "  DEPLOYING: telegram-bridge  (source: ./telegram-bridge)  [PUBLIC]"
echo "=============================================================================="

gcloud run deploy "telegram-bridge" \
    --source "./telegram-bridge" \
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
