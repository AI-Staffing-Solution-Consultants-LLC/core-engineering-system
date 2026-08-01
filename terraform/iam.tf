# IAM: Service account and least-privilege role bindings
# Service account: core-engine-worker@<project>.iam.gserviceaccount.com
# Principle: no broad roles/owner or roles/editor

resource "google_service_account" "core_engine_worker" {
  account_id   = "core-engine-worker"
  display_name = "Core Engineering System Worker"
  description  = "Service account for Track A (control) and Track B (actuator) Cloud Run services"
  project      = var.project_id
}

# Track A — needs invoker (to talk to Track B) and Secret Manager access
resource "google_project_iam_member" "track_a_run_invoker" {
  project = var.project_id
  role    = "roles/run.invoker"
  member  = "serviceAccount:${google_service_account.core_engine_worker.email}"
}

# Track A — Secret Manager accessor (scoped to specific secrets via secrets.tf)
resource "google_project_iam_member" "track_a_secret_accessor" {
  project = var.project_id
  role    = "roles/secretmanager.secretAccessor"
  member  = "serviceAccount:${google_service_account.core_engine_worker.email}"
}

# Track B — scoped logging writer (not admin)
resource "google_project_iam_member" "track_b_log_writer" {
  project = var.project_id
  role    = "roles/logging.logWriter"
  member  = "serviceAccount:${google_service_account.core_engine_worker.email}"
}

# Web Interface Backend — invoker binding for service-to-service auth
resource "google_project_iam_member" "web_interface_backend_run_invoker" {
  project = var.project_id
  role    = "roles/run.invoker"
  member  = "serviceAccount:${google_service_account.core_engine_worker.email}"
}

# Service account token creator (needed for identity-based auth between services)
resource "google_service_account_iam_member" "core_engine_token_creator" {
  service_account_id = google_service_account.core_engine_worker.id
  role               = "roles/iam.serviceAccountTokenCreator"
  member             = "serviceAccount:${google_service_account.core_engine_worker.email}"
}
