variable "name" {
  description = "Instance name (also used to derive the data disk name)."
  type        = string
}

variable "zone" {
  description = "GCP zone, e.g. \"us-central1-a\"."
  type        = string
}

variable "environment" {
  description = "dev or prod, used for labels."
  type        = string
}

variable "subnetwork_id" {
  description = "Subnetwork self_link/id from the network module."
  type        = string
}

variable "machine_type" {
  description = "Compute Engine machine type. Keep it cheap for a classroom VM."
  type        = string
  default     = "e2-small"
}

variable "boot_image" {
  description = "Boot disk image."
  type        = string
  default     = "debian-cloud/debian-12"
}

variable "disk_type" {
  description = "Persistent disk type for the data disk."
  type        = string
  default     = "pd-balanced"
}

variable "disk_size_gb" {
  description = "Size in GB of the data disk."
  type        = number
  default     = 10
}

variable "disk_device_name" {
  description = "Device name used both by the attached_disk block and the startup script to find /dev/disk/by-id/google-<name>."
  type        = string
  default     = "datos"
}

variable "container_name" {
  description = "Docker container name used by the startup script."
  type        = string
  default     = "servicio-patron"
}

variable "container_image" {
  description = "Container image to run, e.g. \"REGION-docker.pkg.dev/PROJECT/REPO/servicio-patron:TAG\". No default: must come from Artifact Registry, never hardcoded here."
  type        = string
}

variable "app_port" {
  description = "Port exposed by the container and opened in the firewall."
  type        = number
  default     = 8080
}
