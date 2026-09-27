# dev environment: wires the modules together. Used from class 2 (VM only)
# through class 5-6 (add GKE) and class 8 (integrator case).
#
# No project id, credentials or other secrets are hardcoded here: they come
# from variables, which in CI are populated from repository variables /
# Workload Identity Federation (see .github/workflows/deploy.yml).

terraform {
  required_version = ">= 1.6"

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}

locals {
  name_prefix = "infra-cloud-dev"
}

module "network" {
  source = "../../modules/network"

  name_prefix = local.name_prefix
  region      = var.region
  app_port    = var.app_port
}

module "artifact_registry" {
  source = "../../modules/artifact-registry"

  project_id    = var.project_id
  region        = var.region
  repository_id = "infra-cloud-template"
}

module "vm" {
  source = "../../modules/vm"

  name            = "${local.name_prefix}-vm"
  zone            = var.zone
  environment     = "dev"
  subnetwork_id   = module.network.subnetwork_id
  container_image = var.servicio_patron_image
  app_port        = var.app_port
}

# GKE is optional in dev: classes 1-4 only need the VM. Toggle it on once
# you reach class 5.
module "gke" {
  source = "../../modules/gke"
  count  = var.enable_gke ? 1 : 0

  name           = "${local.name_prefix}-gke"
  zone           = var.zone
  environment    = "dev"
  network_id     = module.network.network_id
  subnetwork_id  = module.network.subnetwork_id
  max_node_count = 2
}
