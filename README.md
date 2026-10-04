# infra-cloud-template

Repo template de la cátedra (2026). Trae el **servicio patrón** y todo lo que
hace falta para llevarlo de tu laptop a producción a lo largo de las 8 clases:
contenedores, IaC, CI/CD, Kubernetes y observabilidad. Cada estudiante lo
instancia y le suma su propio artefacto. Hay dos pistas de ejemplo: **IA**
(servidor de inferencia) y **BC** (Blockchain: Anvil, contratos y la **línea
base** de una mini-blockchain PoW, de un solo nodo, que extendés en tu Trabajo
Final).

No hace falta entender todo el repo el día 1: cada clase usa una carpeta
puntual. Arrancá por la sección "Primeros 10 minutos" y después seguí la guía
de la clase que te toca en `docs/`.

## Primeros 10 minutos

### 1. Prerrequisitos

| Necesitás | Para qué | Cómo verificarlo |
|---|---|---|
| Linux, macOS o Windows con **WSL2** | Todos los comandos son de bash | `echo $SHELL` |
| **Docker** con el plugin compose v2 | Desde la clase 1 | `docker compose version` |
| **git** | Clonar tu repo | `git --version` |
| **uv** | Correr los tests (`make test-*`) | `uv --version` |
| **make** | Atajos (`make help` los lista) | `make --version` |
| Unos 10 GB libres de disco | Imágenes y el cluster local | `df -h` |

Lo demás (OpenTofu o Terraform, gcloud, kubectl, helm, k3d, k6, Foundry) se
instala en la clase que lo usa. Foundry y k6 ni siquiera hacen falta: el
`Makefile` usa sus imágenes de Docker si no los tenés.

En Windows trabajá **adentro de WSL2** (Ubuntu): ahí `make`, `$PWD` y los
permisos se comportan como en Linux. Instalá uv con
`curl -LsSf https://astral.sh/uv/install.sh | sh`.

### 2. Tu copia del repo

1. En GitHub, en la página de este repo, tocá **Use this template → Create a
   new repository**. No uses *Fork*: en un fork las Actions arrancan
   deshabilitadas y el repo queda atado al original.
2. Cloná tu repo y entrá a la carpeta. **Todos los comandos de las guías se
   corren desde esta carpeta (la raíz del repo)**, salvo que la guía diga otra
   cosa.

```bash
git clone https://github.com/<tu-usuario>/<tu-repo>.git
cd <tu-repo>
make doctor
```

Salida esperada de `make doctor` (las versiones cambian; lo que importa es que
no haya ningún `[FAIL]`):

```
Required
  [ok]   git            git version 2.43.0
  [ok]   docker         Docker version 27.x
  [ok]   docker compose Docker Compose version v2.x
  [ok]   uv             uv 0.x
...
doctor: everything required is installed.
```

Las líneas `[--]` son opcionales: te dicen qué instalar y en qué clase.

### 3. Levantá el servicio patrón

```bash
make compose-up
curl localhost:8080/
curl localhost:8080/healthz
```

Salida esperada:

```
Servicio patron activo. Visitas persistidas en disco: 1
{"status":"ok"}
```

Para bajarlo: `make compose-down` (conserva los datos) o `make compose-reset`
(los borra).

## Mapa por clase

| Clase | Tema | Guía | Qué usás de este repo |
|---|---|---|---|
| 1 | Arquitectura híbrida y cargas stateful sobre Compute Engine | [docs/clase-01.md](docs/clase-01.md) | `app/` en tu laptop y en una VM, con el estado en un disco aparte |
| 2 | IaC con OpenTofu/Terraform sobre GCP | [docs/clase-02.md](docs/clase-02.md) | `terraform/modules/{network,vm,artifact-registry}`, `terraform/envs/dev` |
| 3 | Contenedores con Docker y Artifact Registry | [docs/clase-03.md](docs/clase-03.md) | los `Dockerfile`, `compose/`, el registry `infra-cloud-template` |
| 4 | CI/CD con GitHub Actions y OIDC | [docs/clase-04.md](docs/clase-04.md) | `.github/workflows/ci.yml` (IA y BC) y `contracts.yml` (BC) |
| 5 | Kubernetes: Helm, PV y StatefulSets | [docs/clase-05.md](docs/clase-05.md) | `helm/charts/*` con `values-k3s.yaml` (local) y `terraform/modules/gke` |
| 6 | Observabilidad: Prometheus, Grafana y Loki | [docs/clase-06.md](docs/clase-06.md) | `observability/` completo |
| 7 | IA: Vertex AI, Ollama, vast.ai · BC: Layer 2 (Base Sepolia) | [docs/clase-07.md](docs/clase-07.md) | `model/` (IA) · `contracts/` + `contracts.yml` (BC) |
| 8 | Caso integrador: de git push a producción | [docs/clase-08.md](docs/clase-08.md) | todo el repo, orquestado por `deploy.yml` |

Cada guía tiene la misma estructura: objetivo, prerrequisitos, pasos
numerados con la salida esperada, la pista BC y la pista IA, un recuadro "En
la nube", limpieza y una tabla de errores frecuentes.

## ¿Qué hay acá adentro?

```
app/                 servicio patrón (FastAPI): GET /, /healthz, /metrics,
                     POST /items y GET /items. Estado en /data.
model/               (IA) servidor de inferencia: POST /predict. El modelo
                     (iris) se entrena al construir la imagen.
pow/                 (BC) LÍNEA BASE de un nodo PoW (corre como un nodo):
                     /healthz /metrics /chain /tx /mine, dificultad fija,
                     cadena en /data. Lo que falta (peers, /peers/sync,
                     validar cadenas, consenso, dificultad ajustable, reglas
                     del mempool, concurrencia) está marcado TODO(TF): es tu
                     Trabajo Final.
contracts/           (BC) proyecto Foundry: contrato Counter + tests.
compose/             docker-compose.yml (servicio patrón) y
                     docker-compose.anvil.yml (Anvil + servicio patrón).
terraform/           módulos (network, vm, artifact-registry, gke) y
                     entornos dev/prod, con ejemplos de tfvars y backend.
helm/charts/         servicio-patron, anvil, pow y model. values.yaml es para
                     GKE; values-k3s.yaml, para tu cluster local.
observability/       valores de kube-prometheus-stack y Loki, config de
                     Alloy, ServiceMonitors, dashboards y el exporter de Anvil.
.github/workflows/   ci.yml, contracts.yml y deploy.yml (OIDC, sin claves).
loadtest/            script de k6 y un Job para correrlo dentro del cluster.
scripts/             doctor.sh (make doctor) y compute-tags.sh (tags de CI).
docs/                una guía por clase.
```

## Nombres, puertos y tags (una sola tabla para todo el curso)

| Servicio | Carpeta | Puerto | Imagen local | Imagen en Artifact Registry | Release de Helm |
|---|---|---|---|---|---|
| Servicio patrón | `app/` | 8080 | `app:local` | `$AR/app` | `servicio-patron` |
| Modelo (IA) | `model/` | 8081 | `model:local` | `$AR/model` | `model` |
| Nodo PoW (BC) | `pow/` | 8090 | `pow:local` | `$AR/pow` | `pow` |
| Anvil (BC) | imagen de Foundry | 8545 | `ghcr.io/foundry-rs/foundry:stable` | (no se publica) | `anvil` |
| Exporter de Anvil | `observability/anvil-exporter/` | 9090 | `anvil-exporter:local` | (no se publica) | sidecar del chart `anvil` |

Con estas variables (poné **tus** valores, entre comillas):

```bash
export PROJECT_ID="mi-proyecto-123"        # tu proyecto de GCP, en minúsculas
export REGION="southamerica-east1"         # la región de todo el curso
export ZONE="southamerica-east1-a"
export AR="${REGION}-docker.pkg.dev/${PROJECT_ID}/infra-cloud-template"
echo "$AR"
```

Tags de las imágenes:

- `:local` en tu laptop (`make build`).
- `:v1` la primera vez que subís a mano, en la clase 3.
- `:<sha del commit>` en cada push que publica CI, y `:vX.Y.Z` cuando creás
  un tag de release (`git tag v0.1.0 && git push origin v0.1.0`), desde la
  clase 4. No hay `:latest`: un tag que se mueve no es una versión.

Instalá los charts con el **nombre de release** de la tabla: los nombres DNS,
los dashboards y las guías asumen esos nombres.

## BC: la línea base PoW es el punto de partida de tu TF

El Trabajo Final de BC es **tu propia blockchain PoW con varios nodos, en
producción en la nube**. `pow/` y `helm/charts/pow` no son esa blockchain:
son la línea base de la que partís.

| Ya está (no lo tenés que escribir) | Es tu TF (marcado `TODO(TF)` en el código) |
|---|---|
| `Block`, hash sha256, bloque génesis | dificultad ajustable |
| cadena en JSON en `/data` (sobrevive al pod) | validar una cadena que llega de otro nodo |
| `POST /mine` con un loop de dificultad fija | peers: `GET /peers` y `POST /peers/sync` |
| `/healthz`, `/metrics` (`pow_block_height`), `/chain`, `/tx` en el puerto 8090 | consenso: la cadena más larga y válida gana |
| chart con StatefulSet, un PVC por nodo, Service headless y `PEERS` | reglas del mempool y seguridad ante concurrencia |

Los tests de `pow/tests/` que están en `skip` son la pista: cuando implementes
cada parte, sacales el `skip`. Con `replicaCount: 3` hoy tenés tres cadenas
**independientes**; que converjan es tu trabajo (al menos 2 nodos sincronizando).

## Comandos útiles

```bash
make help            # lista todos los atajos
make doctor          # chequea herramientas, disco y puertos
make test            # todos los tests (app, model, pow, exporter, contratos)
make build           # las imágenes con tag :local
make compose-up      # servicio patrón en :8080
make compose-anvil-up   # Anvil :8545 + servicio patrón :8080
make tf-validate     # valida todo terraform/ sin nube (usa tofu si está)
make helm-lint       # lint de los charts con values.yaml y values-k3s.yaml
make k3d-up && make k3d-images   # cluster local con las imágenes adentro
```

`make tf-validate TF=terraform` fuerza Terraform si tenés los dos.

## Filosofía del repo

- **El disco manda.** El servicio patrón, Anvil y los nodos PoW guardan su
  estado en un path montado (`/data` o `/state`), nunca en el filesystem del
  contenedor. Podés matar el contenedor, el pod o la VM: el estado sobrevive
  porque vive en el disco persistente o el PVC.
- **Todo expone `/metrics` y `/healthz`.** Prometheus desde el día 1, y un
  chequeo de salud que usan Docker, compose, CI y Kubernetes.
- **Sin secretos en el repo.** CI/CD usa OIDC (Workload Identity Federation)
  contra GCP: ni una clave JSON ni un token en ningún archivo. Lo que hace
  falta se carga como variable de repositorio de GitHub.
- **Chico y leíble.** Cada archivo se lee en minutos. Es un repo de cátedra,
  no un framework.

## Si algo falla: índice de problemas

| Si ves esto | Mirá |
|---|---|
| `Cannot connect to the Docker daemon` | Docker no está corriendo. Abrí Docker Desktop o `sudo systemctl start docker`. |
| `port is already allocated` | Otro contenedor usa el puerto: `docker ps`, y `docker rm -f <nombre>` o `make compose-down`. También podés usar `APP_PORT=18080 make compose-up`. |
| `Conflict. The container name ... is already in use` | `docker rm -f <nombre>` y volvé a correr el `docker run`. |
| `curl: (56) Recv failure: Connection reset by peer` | El servicio todavía arranca: esperá 2 segundos o usá `--wait` en compose. |
| `uv: command not found` / `forge: not found` | `make doctor` te dice qué instalar; `make test-contracts` usa Docker si no hay forge. |
| `Backend initialization required` | [clase 2](docs/clase-02.md#errores-frecuentes): el chequeo offline es `init -backend=false` + `validate`, no `plan`. |
| El saldo de Anvil volvió a 10000 ETH | [clase 3](docs/clase-03.md#errores-frecuentes): el volumen de estado no era escribible. |
| Pods en `Pending` | [clase 5](docs/clase-05.md#errores-frecuentes): StorageClass o disco casi lleno. |
| `ErrImageNeverPull` / `ErrImagePull` | [clase 5](docs/clase-05.md#errores-frecuentes): falta `make k3d-images` o el `image.repository`. |
| `publish` aparece gris (skipped) en Actions | [clase 4](docs/clase-04.md#errores-frecuentes): es lo esperado hasta cargar las variables. |

## Convenciones

- Código y comentarios en inglés. Documentación y este README en español
  rioplatense.
- Variables de entorno, nunca valores hardcodeados: `DATA_DIR`, `PORT`,
  `PEERS`, `MODEL_PATH`, etc. Los defaults están en el
  `Dockerfile` de cada servicio.
- Ningún archivo contiene credenciales. Lo que necesita CI/CD (project id,
  proveedor de Workload Identity, cuenta de servicio) es una **variable de
  repositorio** de GitHub; la clave de deploy de testnet (BC) es un *secret*
  de un environment.

## Docente

Dr. David Marcelo Petrocelli · dmpetrocelli@gmail.com
