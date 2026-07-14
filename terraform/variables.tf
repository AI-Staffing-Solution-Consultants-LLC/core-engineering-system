# Input variables for the Core Engineering System Terraform module

variable "project_id" {
  description = "GCP project ID"
  type        = string
  default     = "aissc-core-engine-self-dep"
}

variable "region" {
  description = "GCP region for Cloud Run deployment"
  type        = string
  default     = "us-central1"
}

variable "track_a_image" {
  description = "Container image URI for Track A (control loop)"
  type        = string
  default     = "us-central1-docker.pkg.dev/aissc-core-engine-self-dep/core-engine/track-a:latest"
}

variable "track_b_image" {
  description = "Container image URI for Track B (actuator)"
  type        = string
  default     = "us-central1-docker.pkg.dev/aissc-core-engine-self-dep/core-engine/track-b:latest"
}

variable "alert_email" {
  description = "Email address for Cloud Monitoring alert notifications"
  type        = string
  default     = "alerts@example.com"
}

variable "core_engine_api_key_secret" {
  description = "API key secret value for Core Engine (set via environment or .tfvars, never commit)"
  type        = string
  sensitive   = true
  default     = "placeholder-change-me"
}

variable "track_b_auth_token_secret" {
  description = "Auth token for Track B service-to-service communication"
  type        = string
  sensitive   = true
  default     = "placeholder-change-me"
}
