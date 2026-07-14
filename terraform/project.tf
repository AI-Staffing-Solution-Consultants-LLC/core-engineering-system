# Project-level settings
# Used for project-scoped IAM bindings and API enablement

resource "google_project_service" "required_apis" {
  for_each = toset([
    "run.googleapis.com",
    "cloudbuild.googleapis.com",
    "secretmanager.googleapis.com",
    "monitoring.googleapis.com",
    "logging.googleapis.com",
    "iam.googleapis.com",
  ])
  project = var.project_id
  service = each.key
}
