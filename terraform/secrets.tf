# Secret Manager: runtime secrets bound via per-secret IAM
# Values are placeholders — set actual values via gcloud or Terraform variables

resource "google_secret_manager_secret" "core_engine_api_key" {
  secret_id = "core-engine-api-key"
  project   = var.project_id

  replication {
    auto {}
  }
}

resource "google_secret_manager_secret_version" "core_engine_api_key_v1" {
  secret      = google_secret_manager_secret.core_engine_api_key.id
  secret_data = var.core_engine_api_key_secret
}

# Per-secret access for the worker service account
resource "google_secret_manager_secret_iam_member" "core_engine_secret_access" {
  secret_id = google_secret_manager_secret.core_engine_api_key.secret_id
  project   = var.project_id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.core_engine_worker.email}"
}

resource "google_secret_manager_secret" "track_b_auth_token" {
  secret_id = "track-b-auth-token"
  project   = var.project_id

  replication {
    auto {}
  }
}

resource "google_secret_manager_secret_version" "track_b_auth_token_v1" {
  secret      = google_secret_manager_secret.track_b_auth_token.id
  secret_data = var.track_b_auth_token_secret
}

resource "google_secret_manager_secret_iam_member" "track_b_secret_access" {
  secret_id = google_secret_manager_secret.track_b_auth_token.secret_id
  project   = var.project_id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.core_engine_worker.email}"
}
