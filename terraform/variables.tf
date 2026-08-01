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

variable "sheryl_image" {
  description = "Container image URI for Sheryl Quartet"
  type        = string
  default     = "placeholder-change-me"
}

variable "aura_image" {
  description = "Container image URI for Aura Quartet"
  type        = string
  default     = "placeholder-change-me"
}

variable "malory_image" {
  description = "Container image URI for Malory Quartet"
  type        = string
  default     = "placeholder-change-me"
}

variable "krieger_image" {
  description = "Container image URI for Krieger Quartet"
  type        = string
  default     = "placeholder-change-me"
}

variable "self_remediation_image" {
  description = "Container image URI for Self-Remediation"
  type        = string
  default     = "placeholder-change-me"
}

variable "telegram_bridge_image" {
  description = "Container image URI for Telegram Bridge"
  type        = string
  default     = "placeholder-change-me"
}

variable "web_interface_backend_image" {
  description = "Container image URI for Web Interface backend"
  type        = string
  default     = "us-central1-docker.pkg.dev/aissc-core-engine-self-dep/core-engine/web-interface-backend:latest"
}

variable "tavus_api_key" {
  description = "Tavus API key for Web Interface backend (set via environment or .tfvars, never commit)"
  type        = string
  sensitive   = true
  default     = "placeholder-change-me"
}

variable "web_interface_access_password_hash" {
  description = "Bcrypt hash of the access password for Web Interface frontend (set via environment or .tfvars, never commit)"
  type        = string
  sensitive   = true
  default     = "placeholder-change-me"
}

variable "web_interface_api_token" {
  description = "API token for Web Interface backend auth middleware (set via environment or .tfvars, never commit)"
  type        = string
  sensitive   = true
  default     = "placeholder-change-me"
}
