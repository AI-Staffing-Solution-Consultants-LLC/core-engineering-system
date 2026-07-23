#!/usr/bin/env bash
set -euo pipefail

echo "========================================================================"
echo "[!] SECURING SYSTEM BOUNDARIES: RUNNING INFISICAL AUTHORIZATION SYNC"
echo "========================================================================"

# 1. Login to Infisical Core Vault via your existing Machine Identity
echo "[*] Authenticating Universal Auth Credentials..."
AUTH_RESPONSE=$(curl -s -X POST "https://infisical.com" \
  -H "Content-Type: application/json" \
  -d "{\"clientId\": \"${INFISICAL_CLIENT_ID}\", \"clientSecret\": \"${INFISICAL_CLIENT_SECRET}\"}")

INFISICAL_TOKEN=$(echo "$AUTH_RESPONSE" | grep -o '"accessToken":"[^"]*' | grep -o '[^"]*$')

if [ -z "$INFISICAL_TOKEN" ]; then
    echo "[-] Fatal error: Universal Auth handshake failed."
    exit 1
fi

echo "[+] Trust connection established successfully."

# 2. Function helper to inject scoped credentials to explicit directory paths
inject_secret_to_scope() {
    local secret_name=$1
    local secret_value=$2
    local target_secret_path=$3

    echo "[*] Seeding secret: ${secret_name} into path context: ${target_secret_path}..."
    curl -s -X POST "https://infisical.com{secret_name}" \
      -H "Authorization: Bearer ${INFISICAL_TOKEN}" \
      -H "Content-Type: application/json" \
      -d "{
        \"workspaceId\": \"${INFISICAL_WORKSPACE_ID}\",
        \"environment\": \"production\",
        \"secretPath\": \"${target_secret_path}\",
        \"secretValue\": \"${secret_value}\",
        \"secretType\": \"shared\"
      }" > /dev/null
}

# 3. Synchronize your explicit Google Cloud Vertex Roster credentials across path boundaries
inject_secret_to_scope "GCP_VERTEX_PROJECT_ID" "aissc-core-engine-self-dep" "/CORE-Modules/Inference-Tokenomics"
inject_secret_to_scope "GCP_VERTEX_REGION" "us-central1" "/CORE-Modules/Inference-Tokenomics"
inject_secret_to_scope "GCP_SERVICE_ACCOUNT_KEY_BASE64" "${GCP_SERVICE_ACCOUNT_KEY_BASE64}" "/CORE-Modules/Inference-Tokenomics"

# Synchronize fallback variables for our Cloudflare AI edge matrix
inject_secret_to_scope "OPENROUTER_API_KEY" "${OPENROUTER_API_KEY}" "/CORE-Modules/Inference-Tokenomics"

echo "[+] Success: Infisical secret maps populated for path-aware builds."

