variable "project_id" {
  description = "GCP project id. No default on purpose: never hardcode it."
  type        = string
}

variable "region" {
  description = "GCP region, e.g. \"us-central1\"."
  type        = string
}

variable "zone" {
  description = "GCP zone, e.g. \"us-central1-a\"."
  type        = string
}

variable "servicio_patron_image" {
  description = "Full Artifact Registry image reference for the servicio patron, produced by ci.yml."
  type        = string
}

variable "app_port" {
  type    = number
  default = 8080
}

variable "enable_gke" {
  description = "Set to true starting class 5, once you need Kubernetes."
  type        = bool
  default     = false
}
