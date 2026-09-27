# infra-cloud-template

Repo template de la cátedra (2026). Es el "servicio patrón" y todo lo
que hace falta para llevarlo de tu laptop a producción a lo largo de las 8
clases: contenedores, IaC, CI/CD, Kubernetes y observabilidad. Cada estudiante
lo instancia y le agrega su propio artefacto (trae ejemplos para cargas de IA
y para Web3/Blockchain).

No hace falta entender todo el repo el día 1. Cada clase usa una carpeta
puntual — abajo tenés el mapa completo.

## ¿Qué hay acá adentro?

```
app/              servicio patrón (FastAPI): GET / , GET /healthz, GET /metrics,
                  POST /items y GET /items, con estado persistido en /data.
model/            (IA) servidor de inferencia liviano: POST /predict, /metrics.
                  Modelo de ejemplo (iris) entrenado al construir la imagen.
pow/              (Blockchain) nodo de una mini-blockchain de prueba de trabajo
                  (PoW): /chain /tx /mine /peers /peers/sync /metrics.
contracts/        proyecto Foundry: contrato de ejemplo + tests (`forge test`).
compose/          docker-compose.yml (servicio patrón) y docker-compose.anvil.yml
                  (Anvil + servicio patrón, para el ejemplo Blockchain).
terraform/        módulos (network, vm, artifact-registry, gke) + entornos
                  dev/prod. Nada de project ids ni secretos hardcodeados.
helm/charts/      servicio-patron, anvil, pow y model: charts para Kubernetes.
observability/    valores de kube-prometheus-stack y Loki, ServiceMonitors,
                  dashboards de Grafana y un exporter chiquito para Anvil.
.github/workflows/ ci.yml, deploy.yml y contracts.yml (CI/CD con OIDC, sin claves).
loadtest/         script de k6 para generar carga y disparar el HPA.
docs/             una guía corta por clase (clase-01.md … clase-08.md).
```

## Filosofía del repo

- **El disco manda.** El servicio patrón, Anvil y los nodos PoW escriben su
  estado en un path montado (`/data` o `/state`), nunca en el filesystem
  efímero del contenedor. Podés matar el contenedor o la VM: el estado
  sobrevive porque vive en el disco persistente / PVC.
- **Todo expone `/metrics`.** Cada servicio habla Prometheus desde el día 1,
  así la clase de observabilidad (clase 6) no arranca de cero.
- **Sin secretos en el repo.** CI/CD usa OIDC (Workload Identity Federation)
  contra GCP: ni una clave JSON, ni un token, en ningún archivo.
- **Chico y leíble.** Cada archivo está pensado para leerse en minutos, no en
  horas. Es un repo de cátedra, no un framework.

## Mapa por clase

| Clase | Tema | Qué usás de este repo |
|---|---|---|
| 1 | Arquitectura híbrida y cargas stateful sobre Compute Engine | `app/` corriendo a mano en una VM, con el disco persistente montado en `/data` |
| 2 | IaC con Terraform sobre GCP | `terraform/modules/network` y `terraform/modules/vm`, `terraform/envs/dev` |
| 3 | Contenedores con Docker y Artifact Registry | `app/Dockerfile`, `terraform/modules/artifact-registry`, `compose/` |
| 4 | CI/CD con GitHub Actions y OIDC | `.github/workflows/ci.yml` (IA/BC) y `contracts.yml` (BC) |
| 5 | Kubernetes con GKE: Helm, PV y StatefulSets | `terraform/modules/gke`, `helm/charts/servicio-patron`, `helm/charts/anvil` |
| 6 | Observabilidad: Prometheus, Grafana y Loki | `observability/` completo |
| 7 | IA: Vertex AI, Ollama, vast.ai · BC: Layer 2 (Base Sepolia) | `model/` (IA) · `contracts/` + `contracts.yml` (BC) |
| 8 | Caso integrador: git push → producción | Todo el repo, orquestado por `deploy.yml` |

Ver el detalle clase por clase en `docs/clase-01.md` … `docs/clase-08.md`.

## Cómo lo corrés en tu laptop

Necesitás Docker (y opcionalmente `uv`, Terraform/OpenTofu, Helm y `forge`
de Foundry si querés ir más allá del servicio patrón).

```bash
# Levantar el servicio patrón solo
make compose-up
curl localhost:8080/
curl localhost:8080/metrics

# Levantar Anvil + servicio patrón (ejemplo Blockchain)
make compose-anvil-up

# Correr los tests de cada servicio
make test

# Bajar todo
make compose-down
```

Ver `Makefile` para el resto de los targets (build de imágenes, `terraform
fmt`/`validate`, `helm lint`/`template`, load test con k6).

## Convenciones

- Código y comentarios: inglés. Documentación y este README: español
  rioplatense.
- Variables de entorno, nunca valores hardcodeados: `DATA_DIR`, `PORT`,
  `DIFFICULTY`, `PEERS`, `MODEL_PATH`, etc. Ver el `Dockerfile` de cada
  servicio para los defaults.
- Ningún archivo de este repo contiene credenciales. Todo lo que hace falta
  para CI/CD (project id, proveedor de Workload Identity, cuenta de
  servicio) se configura como **variable de repositorio** de GitHub, no como
  secreto ni como texto hardcodeado.

## Docente

Dr. David Marcelo Petrocelli — dmpetrocelli@gmail.com
