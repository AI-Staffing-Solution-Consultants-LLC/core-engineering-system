# SOP-001: OpenViking System Architecture

**Namespace:** openviking  
**Status:** Active  
**Last Updated:** 2026-07-21

## Overview

OpenViking is a multi-cluster observability platform deployed on Google Kubernetes Engine (GKE) with Cloud Run sidecars for stateless processing. The system ingests metrics, logs, and traces from production workloads and surfaces anomalies through a ReAct-style control loop (Track A/B pattern).

## Architectural Layers

### 1. Data Ingestion Layer
- **Metrics:** Prometheus + Google Cloud Monitoring
- **Logs:** Fluentd → Cloud Logging → Pub/Sub
- **Traces:** OpenTelemetry collectors → Cloud Trace

### 2. Control Plane (Track A)
- Flask-based control loop on Cloud Run (us-central1)
- RAG corpus search for historical incident matching
- Constitutional AI policy enforcement via OPA/Rego
- Tamper-evident ledger (SHA-256 chained JSONL)

### 3. Actuation Plane (Track B)
- Sandboxed tool execution with allowlist validation
- Subprocess isolation (15s timeout, 8192 byte output limit)
- Metacharacter blocklist for injection prevention

### 4. Persistence Layer
- Ledger: daily-rotating JSONL files with chain hashes
- RAG Corpus: Markdown-based knowledge base under `/rag/docs/`
- Secrets: Secret Manager (GCP), never in logs or commits

## Service Topology

```
Operator → Track A (Cloud Run, port 8080, internal-only)
              ↕
           Track B (Cloud Run, port 8081, internal-only)
              ↕
           GKE Cluster (us-central1)
```

## Resource Constraints
- CPU: 1 vCPU per service
- Memory: 512Mi (fallback to 256Mi on quota errors)
- Instance scaling: 0–1 (free tier)
- Region: us-central1 only

## Key Dependencies
- GCP Project: `aissc-core-engine-self-dep`
- Service Account: `core-engine-worker`
- Policy Engine: OPA/Rego rules in `/policy/*.rego`

## Monitoring & Alerting
- Cloud Monitoring alert policies for request count and latency
- Ledger integrity verified via chain hash validation
- Health check endpoints at `/healthz` on both tracks
