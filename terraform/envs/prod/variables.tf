variable "project_id" {
  description = "GCP project id. No default on purpose: never hardcode it."
  type        = string
}

variable "region" {
  description = "GCP region. The course uses southamerica-east1 (Sao Paulo) everywhere."
  type        = string
  default     = "southamerica-east1"
}

variable "zone" {
  description = "GCP zone inside the region."
  type        = string
  default     = "southamerica-east1-a"
}

variable "servicio_patron_image" {
  description = "Image the VM runs (only used when enable_vm = true), e.g. southamerica-east1-docker.pkg.dev/PROJECT_ID/infra-cloud-template/app:<sha>."
  type        = string
  default     = ""
}

variable "app_port" {
  type    = number
  default = 8080
}

variable "enable_artifact_registry" {
  description = "Create the Artifact Registry repository infra-cloud-template. ONE env per project creates it (dev by default); a second one would fail with 409 already exists."
  type        = bool
  default     = false
}

variable "enable_vm" {
  description = "Create the VM + data disk of classes 1-2."
  type        = bool
  default     = false
}

variable "enable_gke" {
  description = "Create the GKE cluster (class 5 onward). It costs money while it exists: destroy it after class."
  type        = bool
  default     = true
}
