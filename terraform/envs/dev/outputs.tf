output "vm_external_ip" {
  value = module.vm.external_ip
}

output "artifact_registry_url" {
  value = module.artifact_registry.repository_url
}

output "gke_cluster_name" {
  value = var.enable_gke ? module.gke[0].cluster_name : null
}
