# Clase 2 — IaC con Terraform sobre GCP

## Qué mirás de este repo

- `terraform/modules/network/`: VPC, subred y las reglas de firewall
  mínimas (SSH, el puerto de la app, health checks).
- `terraform/modules/vm/`: la VM de la clase 1, pero declarada como código:
  disco de datos aparte, script de arranque templatizado.
- `terraform/envs/dev/main.tf`: cómo se combinan los módulos para armar un
  entorno completo.

## La idea central

Todo lo que hiciste a mano en la clase 1 (crear la VM, el disco, montarlo,
abrir el firewall) ahora es un plan reproducible. `terraform plan` te
muestra qué va a cambiar *antes* de tocar nada; nadie aplica un cambio a
ciegas.

## Para probarlo vos

```bash
cd terraform/envs/dev
terraform init -backend=false   # sin backend remoto, para inspeccionar en local
terraform validate
terraform plan \
  -var="project_id=tu-proyecto" \
  -var="region=us-central1" \
  -var="zone=us-central1-a" \
  -var="servicio_patron_image=us-central1-docker.pkg.dev/tu-proyecto/infra-cloud-template/app:latest"
```

No hay ningún project id ni credencial hardcodeada: todo entra por
`-var` (o, en CI, por variables de repositorio — ver `docs/clase-04.md`).

## Drift

Si alguien toca la consola a mano (por ejemplo, cambia el firewall desde la
UI de GCP), el próximo `terraform plan` lo va a mostrar como un cambio a
revertir. Ese es el foro de esta clase.
