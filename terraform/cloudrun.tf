# Cloud Run services: Track A (control loop) and Track B (actuator)
# Auth: --no-allow-unauthenticated on both services
# Sizing: fits GCP free tier (cpu=1, memory=512Mi, min_instances=0, max_instances=1)

# --- Track A — Control & Planning Loop ---
resource "google_cloud_run_v2_service" "track_a" {
  name     = "track-a-control-loop"
  location = var.region
  project  = var.project_id

  template {
    containers {
      image = var.track_a_image
      ports {
        container_port = 8080
      }
      resources {
        limits = {
          cpu    = "1"
          memory = "512Mi"
        }
      }

      # Start the Flask app via gunicorn (production WSGI server)
      startup_probe {
        initial_delay_seconds = 10
        timeout_seconds       = 5
        period_seconds        = 10
        failure_threshold     = 3
        tcp_socket {
          port = 8080
        }
      }

      liveness_probe {
        http_get {
          path = "/healthz"
          port = 8080
        }
      }

      env {
        name  = "TRACK_B_URL"
        value = google_cloud_run_v2_service.track_b.uri
      }
      env {
        name  = "LEDGER_PATH"
        value = "/var/log/ledger"
      }
    }

    scaling {
      min_instance_count = 0
      max_instance_count = 1
    }

    service_account = google_service_account.core_engine_worker.email
  }

  # Auth gate: no unauthenticated access (Constitutional AI enforcement)
  ingress = "INGRESS_TRAFFIC_INTERNAL_ONLY"

  depends_on = [google_project_service.required_apis]
}

# Auth gate: no public access for Track A.
# INGRESS_TRAFFIC_INTERNAL_ONLY already blocks unauthenticated access.
# Service-to-service auth uses the service account identity (roles/run.invoker at project level in iam.tf).
# No allUsers binding — Constitutional AI enforcement at the infrastructure layer.

# --- Track B — Actuator ---
resource "google_cloud_run_v2_service" "track_b" {
  name     = "track-b-actuator"
  location = var.region
  project  = var.project_id

  template {
    containers {
      image = var.track_b_image
      ports {
        container_port = 8081
      }
      resources {
        limits = {
          cpu    = "1"
          memory = "512Mi"
        }
      }

      startup_probe {
        initial_delay_seconds = 10
        timeout_seconds       = 5
        period_seconds        = 10
        failure_threshold     = 3
        tcp_socket {
          port = 8081
        }
      }

      liveness_probe {
        http_get {
          path = "/healthz"
          port = 8081
        }
      }

      env {
        name  = "LEDGER_PATH"
        value = "/var/log/ledger"
      }
    }

    scaling {
      min_instance_count = 0
      max_instance_count = 1
    }

    service_account = google_service_account.core_engine_worker.email
  }

  ingress = "INGRESS_TRAFFIC_INTERNAL_ONLY"

  depends_on = [google_project_service.required_apis]
}

# IAM: only the service account can invoke Track B
resource "google_cloud_run_service_iam_member" "track_b_invoker" {
  location = google_cloud_run_v2_service.track_b.location
  project  = google_cloud_run_v2_service.track_b.project
  service  = google_cloud_run_v2_service.track_b.name
  role     = "roles/run.invoker"
  member   = "serviceAccount:${google_service_account.core_engine_worker.email}"
}
