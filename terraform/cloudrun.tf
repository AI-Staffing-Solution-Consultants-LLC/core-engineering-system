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

# --- Sheryl Quartet ---
resource "google_cloud_run_v2_service" "sheryl_quartet" {
  name     = "sheryl-quartet"
  location = var.region
  project  = var.project_id

  template {
    containers {
      image = var.sheryl_image
      ports {
        container_port = 8083
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
          port = 8083
        }
      }

      liveness_probe {
        http_get {
          path = "/healthz"
          port = 8083
        }
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

resource "google_cloud_run_service_iam_member" "sheryl_quartet_invoker" {
  location = google_cloud_run_v2_service.sheryl_quartet.location
  project  = google_cloud_run_v2_service.sheryl_quartet.project
  service  = google_cloud_run_v2_service.sheryl_quartet.name
  role     = "roles/run.invoker"
  member   = "serviceAccount:${google_service_account.core_engine_worker.email}"
}

# --- Aura Quartet ---
resource "google_cloud_run_v2_service" "aura_quartet" {
  name     = "aura-quartet"
  location = var.region
  project  = var.project_id

  template {
    containers {
      image = var.aura_image
      ports {
        container_port = 8084
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
          port = 8084
        }
      }

      liveness_probe {
        http_get {
          path = "/healthz"
          port = 8084
        }
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

resource "google_cloud_run_service_iam_member" "aura_quartet_invoker" {
  location = google_cloud_run_v2_service.aura_quartet.location
  project  = google_cloud_run_v2_service.aura_quartet.project
  service  = google_cloud_run_v2_service.aura_quartet.name
  role     = "roles/run.invoker"
  member   = "serviceAccount:${google_service_account.core_engine_worker.email}"
}

# --- Malory Quartet ---
resource "google_cloud_run_v2_service" "malory_quartet" {
  name     = "malory-quartet"
  location = var.region
  project  = var.project_id

  template {
    containers {
      image = var.malory_image
      ports {
        container_port = 8085
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
          port = 8085
        }
      }

      liveness_probe {
        http_get {
          path = "/healthz"
          port = 8085
        }
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

resource "google_cloud_run_service_iam_member" "malory_quartet_invoker" {
  location = google_cloud_run_v2_service.malory_quartet.location
  project  = google_cloud_run_v2_service.malory_quartet.project
  service  = google_cloud_run_v2_service.malory_quartet.name
  role     = "roles/run.invoker"
  member   = "serviceAccount:${google_service_account.core_engine_worker.email}"
}

# --- Krieger Quartet ---
resource "google_cloud_run_v2_service" "krieger_quartet" {
  name     = "krieger-quartet"
  location = var.region
  project  = var.project_id

  template {
    containers {
      image = var.krieger_image
      ports {
        container_port = 8086
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
          port = 8086
        }
      }

      liveness_probe {
        http_get {
          path = "/healthz"
          port = 8086
        }
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

resource "google_cloud_run_service_iam_member" "krieger_quartet_invoker" {
  location = google_cloud_run_v2_service.krieger_quartet.location
  project  = google_cloud_run_v2_service.krieger_quartet.project
  service  = google_cloud_run_v2_service.krieger_quartet.name
  role     = "roles/run.invoker"
  member   = "serviceAccount:${google_service_account.core_engine_worker.email}"
}

# --- Self-Remediation ---
resource "google_cloud_run_v2_service" "self_remediation" {
  name     = "self-remediation"
  location = var.region
  project  = var.project_id

  template {
    containers {
      image = var.self_remediation_image
      ports {
        container_port = 8087
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
          port = 8087
        }
      }

      liveness_probe {
        http_get {
          path = "/healthz"
          port = 8087
        }
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

resource "google_cloud_run_service_iam_member" "self_remediation_invoker" {
  location = google_cloud_run_v2_service.self_remediation.location
  project  = google_cloud_run_v2_service.self_remediation.project
  service  = google_cloud_run_v2_service.self_remediation.name
  role     = "roles/run.invoker"
  member   = "serviceAccount:${google_service_account.core_engine_worker.email}"
}

# --- Telegram Bridge ---
resource "google_cloud_run_v2_service" "telegram_bridge" {
  name     = "telegram-bridge"
  location = var.region
  project  = var.project_id

  template {
    containers {
      image = var.telegram_bridge_image
      ports {
        container_port = 8088
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
          port = 8088
        }
      }

      liveness_probe {
        http_get {
          path = "/healthz"
          port = 8088
        }
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

resource "google_cloud_run_service_iam_member" "telegram_bridge_invoker" {
  location = google_cloud_run_v2_service.telegram_bridge.location
  project  = google_cloud_run_v2_service.telegram_bridge.project
  service  = google_cloud_run_v2_service.telegram_bridge.name
  role     = "roles/run.invoker"
  member   = "serviceAccount:${google_service_account.core_engine_worker.email}"
}

# --- Web Interface Backend ---
# Publicly reachable from Cloudflare Pages frontend, but still requires auth token.
# --no-allow-unauthenticated: Constitutional AI enforcement at infra layer.
# INGRESS_TRAFFIC_ALL: browser-facing backend must accept external HTTPS.
resource "google_cloud_run_v2_service" "web_interface_backend" {
  name     = "web-interface-backend"
  location = var.region
  project  = var.project_id

  template {
    containers {
      image = var.web_interface_backend_image
      ports {
        container_port = 3001
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
          port = 3001
        }
      }

      liveness_probe {
        http_get {
          path = "/healthz"
          port = 3001
        }
      }

      env {
        name  = "LEDGER_PATH"
        value = "/var/log/ledger"
      }
      env {
        name  = "TRACK_A_URL"
        value = google_cloud_run_v2_service.track_a.uri
      }
      env {
        name  = "TRACK_B_URL"
        value = google_cloud_run_v2_service.track_b.uri
      }
      env {
        name  = "SHERYL_URL"
        value = google_cloud_run_v2_service.sheryl_quartet.uri
      }
      env {
        name  = "TELEGRAM_BRIDGE_URL"
        value = google_cloud_run_v2_service.telegram_bridge.uri
      }
      env {
        name  = "AURA_URL"
        value = google_cloud_run_v2_service.aura_quartet.uri
      }
      env {
        name  = "MALORY_URL"
        value = google_cloud_run_v2_service.malory_quartet.uri
      }
      env {
        name  = "KRIEGER_URL"
        value = google_cloud_run_v2_service.krieger_quartet.uri
      }
      env {
        name  = "SELF_REMEDIATION_URL"
        value = google_cloud_run_v2_service.self_remediation.uri
      }
      env {
        name  = "TAVUS_API_KEY"
        value = var.tavus_api_key
      }
      env {
        name  = "API_TOKEN"
        value = var.web_interface_api_token
      }
      env {
        name  = "ACCESS_PASSWORD_HASH"
        value = var.web_interface_access_password_hash
      }
    }

    scaling {
      min_instance_count = 0
      max_instance_count = 1
    }

    service_account = google_service_account.core_engine_worker.email
  }

  ingress = "INGRESS_TRAFFIC_ALL"

  depends_on = [google_project_service.required_apis]
}

resource "google_cloud_run_service_iam_member" "web_interface_backend_invoker" {
  location = google_cloud_run_v2_service.web_interface_backend.location
  project  = google_cloud_run_v2_service.web_interface_backend.project
  service  = google_cloud_run_v2_service.web_interface_backend.name
  role     = "roles/run.invoker"
  member   = "serviceAccount:${google_service_account.core_engine_worker.email}"
}
