# Cloud Monitoring alerting policies
# One alert per Track on request_count and request_latencies

resource "google_monitoring_notification_channel" "email" {
  display_name = "Core Engine Alerts"
  type         = "email"
  project      = var.project_id

  labels = {
    email_address = var.alert_email
  }
}

# --- Track A alerts ---

resource "google_monitoring_alert_policy" "track_a_request_count" {
  display_name = "Track A — High Request Count"
  project      = var.project_id
  combiner     = "OR"

  conditions {
    display_name = "Request count exceeds threshold"
    condition_threshold {
      filter     = "resource.type = \"cloud_run_revision\" AND resource.labels.service_name = \"track-a-control-loop\" AND metric.type = \"run.googleapis.com/request_count\""
      duration   = "300s"
      comparison = "COMPARISON_GT"
      threshold_value = 100
      aggregations {
        alignment_period   = "60s"
        per_series_aligner = "ALIGN_RATE"
      }
    }
  }

  notification_channels = [google_monitoring_notification_channel.email.id]
}

resource "google_monitoring_alert_policy" "track_a_latency" {
  display_name = "Track A — High Latency"
  project      = var.project_id
  combiner     = "OR"

  conditions {
    display_name = "P99 latency exceeds threshold"
    condition_threshold {
      filter     = "resource.type = \"cloud_run_revision\" AND resource.labels.service_name = \"track-a-control-loop\" AND metric.type = \"run.googleapis.com/request_latencies\""
      duration   = "300s"
      comparison = "COMPARISON_GT"
      threshold_value = 2000  # ms
      aggregations {
        alignment_period    = "60s"
        per_series_aligner  = "ALIGN_PERCENTILE_99"
      }
    }
  }

  notification_channels = [google_monitoring_notification_channel.email.id]
}

# --- Track B alerts ---

resource "google_monitoring_alert_policy" "track_b_request_count" {
  display_name = "Track B — High Request Count"
  project      = var.project_id
  combiner     = "OR"

  conditions {
    display_name = "Request count exceeds threshold"
    condition_threshold {
      filter     = "resource.type = \"cloud_run_revision\" AND resource.labels.service_name = \"track-b-actuator\" AND metric.type = \"run.googleapis.com/request_count\""
      duration   = "300s"
      comparison = "COMPARISON_GT"
      threshold_value = 100
      aggregations {
        alignment_period   = "60s"
        per_series_aligner = "ALIGN_RATE"
      }
    }
  }

  notification_channels = [google_monitoring_notification_channel.email.id]
}

resource "google_monitoring_alert_policy" "track_b_latency" {
  display_name = "Track B — High Latency"
  project      = var.project_id
  combiner     = "OR"

  conditions {
    display_name = "P99 latency exceeds threshold"
    condition_threshold {
      filter     = "resource.type = \"cloud_run_revision\" AND resource.labels.service_name = \"track-b-actuator\" AND metric.type = \"run.googleapis.com/request_latencies\""
      duration   = "300s"
      comparison = "COMPARISON_GT"
      threshold_value = 2000  # ms
      aggregations {
        alignment_period    = "60s"
        per_series_aligner  = "ALIGN_PERCENTILE_99"
      }
    }
  }

  notification_channels = [google_monitoring_notification_channel.email.id]
}
