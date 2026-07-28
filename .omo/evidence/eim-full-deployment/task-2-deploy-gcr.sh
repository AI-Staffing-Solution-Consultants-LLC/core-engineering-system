=== Task 2: deploy-gcr.sh — Verification Report ===
Timestamp: $(date -u +"%Y-%m-%dT%H:%M:%SZ")

--- Acceptance Criteria ---

[PASS] test -f deploy-gcr.sh && test -x deploy-gcr.sh
       File exists and is executable (chmod +x applied)

[PASS] bash -n deploy-gcr.sh
       Bash syntax check: exit 0, no errors

[PASS] grep -c "allow-unauthenticated" deploy-gcr.sh
       Count: 1 (telegram-bridge only)

--- Service Inventory ---

8 services deployed to aissc-core-engine-self-dep (us-central1):

  1. track-a-control-loop    (source: ./track-a)                    port 8080  internal
  2. track-b-actuator        (source: ./track-b)                    port 8081  internal
  3. sheryl-agent            (source: ./executive-quartet/sheryl)   port 8083  internal
  4. aura-agent              (source: ./executive-quartet/aura)     port 8084  internal
  5. malory-agent            (source: ./executive-quartet/malory)   port 8085  internal
  6. krieger-agent           (source: ./executive-quartet/krieger)  port 8086  internal
  7. self-remediation         (source: ./self-remediation)           port 8087  internal
  8. telegram-bridge          (source: ./telegram-bridge)            port 8088  PUBLIC

--- Auth Policy ---

  --allow-unauthenticated:   telegram-bridge only (1 occurrence in file)
  --no-allow-unauthenticated:  removed (default-private auth on all internal services)
  --ingress internal:         deploy_internal() helper (applied to services 1-7)
  --ingress:                 NOT set on telegram-bridge (external by default)

--- Sizing ---

  All services: --cpu=1 --memory=512Mi --min-instances=0 --max-instances=1

--- Service Account ---

  core-engine-worker@aissc-core-engine-self-dep.iam.gserviceaccount.com

--- APIs ---

  gcloud services enable run.googleapis.com cloudbuild.googleapis.com

--- Summary Output ---

  gcloud run services list --format='table(name, status.address.url, ...)' printed at end.
