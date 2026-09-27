variable "name_prefix" {
  description = "Prefix used to name every resource in this module (e.g. \"infra-cloud-dev\")."
  type        = string
}

variable "region" {
  description = "GCP region for the subnet."
  type        = string
}

variable "subnet_cidr" {
  description = "CIDR range for the single subnet."
  type        = string
  default     = "10.10.0.0/24"
}

variable "app_port" {
  description = "TCP port the servicio patron / model / pow node listens on."
  type        = number
  default     = 8080
}

variable "ssh_source_ranges" {
  description = "Source IP ranges allowed to SSH into instances tagged \"ssh\"."
  type        = list(string)
  default     = ["0.0.0.0/0"]
}
