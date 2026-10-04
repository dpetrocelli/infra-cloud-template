# Clase 3: Contenedores con Docker y Artifact Registry

## Objetivo

"En mi máquina anda" se resuelve empaquetando el runtime completo (código +
dependencias) en una imagen, y publicándola en un registry del que cualquier
máquina la puede bajar.

Al terminar tenés:

1. Las imágenes del repo construidas y probadas en tu laptop.
2. El servicio patrón (y en BC, Anvil) con compose, con el estado en volúmenes que sobreviven a `down`/`up`.
3. Tu imagen publicada en Artifact Registry como `$AR/app:v1` y bajada desde otra máquina.

## Prerrequisitos

- [ ] `make doctor` sin `[FAIL]` y estás en la raíz del repo.
- [ ] Nada corriendo en 8080 ni en 8545. Si quedó el contenedor de la clase 1:
      `docker rm -f servicio-patron`.
- [ ] Para la parte en la nube: las variables de la tabla del
      [README](../README.md#nombres-puertos-y-tags-una-sola-tabla-para-todo-el-curso)
      (`PROJECT_ID`, `REGION`, `AR`).

## Pasos

### 1. Construí las imágenes

```bash
make build
docker images --format '{{.Repository}}:{{.Tag}}  {{.Size}}' | grep ':local'
```

Esperado (aproximado, según tu Docker):

```
app:local             256MB
model:local           635MB
pow:local             259MB
anvil-exporter:local  259MB
```

La base `python:3.12-slim` ya pesa unos 190 MB. El modelo pesa más por
scikit-learn, numpy y scipy. Los warnings `Running pip as the 'root' user` del
build no son errores.

### 2. Corré una imagen con un volumen con nombre

```bash
docker run -d --name servicio-patron -p 8080:8080 -v servicio-patron-data:/data app:local
until curl -sf localhost:8080/healthz; do sleep 1; done; echo
curl localhost:8080/
curl -s -X POST localhost:8080/items -H 'Content-Type: application/json' -d '{"name":"hola"}'; echo
docker rm -f servicio-patron
docker run -d --name servicio-patron -p 8080:8080 -v servicio-patron-data:/data app:local
until curl -sf localhost:8080/healthz; do sleep 1; done; echo
curl localhost:8080/
docker rm -f servicio-patron
```

Esperado: el segundo `curl localhost:8080/` dice `Visitas persistidas en disco: 2`.
El campo del item se llama `name` (con `{"item": ...}` la API responde 422).

Un volumen con nombre (`servicio-patron-data`) lo crea Docker y es escribible
por el contenedor; no hace falta `--user` como con la carpeta de la clase 1.

### 3. Lo mismo con compose

```bash
make compose-up            # = docker compose -f compose/docker-compose.yml up -d --build --wait
curl localhost:8080/
make compose-down          # baja el contenedor, CONSERVA el volumen
make compose-up
curl localhost:8080/       # el contador sigue
make compose-reset         # baja todo y BORRA el volumen
```

`--wait` espera al healthcheck: cuando el comando termina, el servicio ya
contesta. `docker compose ps` muestra `(healthy)`.

### 4. Buenas prácticas que ya trae el repo

- Base `-slim`, `pip install --no-cache-dir`, un proceso y un puerto por imagen.
- `.dockerignore` en cada carpeta: los tests y los cachés no entran a la imagen.
- `HEALTHCHECK` contra `/healthz` en cada `Dockerfile`.
- El modelo se entrena **durante el build** (`RUN python train.py` en
  `model/Dockerfile`), no en cada arranque.
- Sin `VOLUME` en los Dockerfile: montás `/data` vos, explícitamente.

Multi-stage: sirve cuando el build necesita compiladores o herramientas que no
querés en la imagen final (Go, Rust, wheels con C). Para estas imágenes de
Python puro casi no achica (lo medimos: 623 MB contra 621 MB en `model/`).

Usuario no root: si agregás `USER` a un Dockerfile, creá el usuario con un uid
fijo (`useradd --create-home --uid 1000 appuser`) y asegurate de que el disco
sea suyo (`sudo chown -R 1000:1000 /mnt/disks/datos`). Si no, el servicio
responde 500 y en `docker logs` aparece `PermissionError`.

## Pista BC: Anvil + servicio patrón con compose

```bash
make compose-anvil-up      # Anvil en :8545 y el servicio patrón en :8080
docker compose -f compose/docker-compose.anvil.yml logs anvil | sed -n '/Available Accounts/,/Wallet/p' | head -8
```

Ahí aparecen las cuentas de prueba y sus claves privadas. Son **públicas** (las
mismas en cualquier Anvil): sirven solo para esta red local.

Foundry no hace falta en tu máquina: `cast` corre adentro del contenedor.

```bash
DC="docker compose -f compose/docker-compose.anvil.yml"
KEY0=0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80   # cuenta (0) de Anvil
ACC1=0x70997970C51812dc3A010C7d01b50e0d17dc79C8                           # cuenta (1)
$DC exec anvil cast send --rpc-url http://localhost:8545 --private-key $KEY0 --value 1ether $ACC1
$DC exec anvil cast block-number --rpc-url http://localhost:8545
$DC exec anvil cast balance $ACC1 --ether --rpc-url http://localhost:8545
```

Esperado: bloque `1` y saldo `10001.000000000000000000`.

Ahora la prueba de persistencia:

```bash
make compose-anvil-down    # down SIN -v
make compose-anvil-up
$DC exec anvil cast block-number --rpc-url http://localhost:8545   # sigue en 1
$DC exec anvil ls -la /state                                        # anvil-state.json
```

Cómo lo logra el compose (está comentado en el archivo):

- `anvil-state-init` le da el volumen al uid 1000 antes de arrancar Anvil. Sin
  eso Anvil no puede escribir y **no avisa**: la cadena vuelve a cero en cada
  reinicio.
- `--state-interval 5` guarda cada 5 segundos, así un `kill` pierde a lo sumo 5 s.
- `entrypoint: ["anvil"]` hace que Anvil reciba la señal de stop y guarde al salir.
- `FOUNDRY_TAG` (por defecto `stable`) fija la versión de Foundry.

Limpieza: `make compose-anvil-reset` (borra la cadena).

## Pista IA: el servidor de inferencia

```bash
docker run -d --name model -p 8081:8081 model:local
until curl -sf localhost:8081/healthz; do sleep 1; done; echo
curl -s -X POST localhost:8081/predict -H 'Content-Type: application/json' \
  -d '{"features": [5.1, 3.5, 1.4, 0.2]}'; echo
curl -s localhost:8081/metrics | grep '^model_predictions_total'
docker rm -f model
```

Esperado: `{"class":"setosa","confidence":0.9...}` y `model_predictions_total 1.0`.
`/healthz` responde 503 mientras el modelo carga y 200 cuando ya está listo.
En `http://localhost:8081/docs` tenés la API interactiva.

Para tu propio modelo: los pesos van **adentro de la imagen** (como acá) o se
bajan de un bucket al arrancar a un disco montado; nunca en cada request.

> ### En la nube (Artifact Registry)
>
> Un solo repositorio para todo el curso: `infra-cloud-template`, en
> `southamerica-east1`. Si aplicaste `terraform/envs/dev` en la clase 2 ya
> existe; si no, crealo **una sola vez** de una de estas dos formas (no las dos:
> la segunda falla con "already exists"):
>
> ```bash
> export PROJECT_ID="mi-proyecto-123" REGION="southamerica-east1"
> export AR="${REGION}-docker.pkg.dev/${PROJECT_ID}/infra-cloud-template"
> echo "$AR"     # revisalo: minúsculas, sin espacios, sin <...>
> # opción A, con terraform (clase 2): ya está.
> # opción B, a mano:
> gcloud artifacts repositories create infra-cloud-template --repository-format=docker --location="$REGION"
> ```
>
> Subí la imagen:
>
> ```bash
> gcloud auth configure-docker "${REGION}-docker.pkg.dev" --quiet
> docker tag app:local "$AR/app:v1"
> docker push "$AR/app:v1"
> gcloud artifacts docker images list "$AR"
> ```
>
> Bajala en otra máquina (por ejemplo la VM de la clase 1). En la VM los
> comandos de docker van con `sudo`, así que la autenticación también:
>
> ```bash
> sudo gcloud auth configure-docker southamerica-east1-docker.pkg.dev --quiet
> sudo docker rm -f servicio-patron 2>/dev/null
> sudo docker run -d --name servicio-patron -p 8080:8080 -v /mnt/disks/datos:/data \
>   southamerica-east1-docker.pkg.dev/<tu-proyecto>/infra-cloud-template/app:v1
> ```
>
> BC: `docker tag pow:local "$AR/pow:v1"`. IA: `docker tag model:local "$AR/model:v1"`.
> Mismo `docker push`.

## Limpieza

```bash
docker rm -f servicio-patron model 2>/dev/null
make compose-reset compose-anvil-reset
docker volume rm servicio-patron-data 2>/dev/null
```

En GCP las imágenes ocupan espacio (y se cobra pasado el free tier):
`gcloud artifacts docker images delete "$AR/app:v1"` cuando ya no la uses.

## Errores frecuentes

| Si ves | Causa | Hacé |
|---|---|---|
| `422 Unprocessable Entity` en `POST /items` | El JSON no tiene `name`, o falta `-H 'Content-Type: application/json'` | `-d '{"name":"hola"}'` con el header |
| `500` y `PermissionError` en `docker logs` | La imagen corre como no root y `/data` es de root | `sudo chown -R 1000:1000 <dir>` o un volumen con nombre |
| El saldo de Anvil volvió a 10000 ETH / bloque 0 | El volumen de estado no era escribible (o borraste con `down -v`) | Usá el compose del repo tal cual; `ls -la /state` adentro del contenedor tiene que mostrar `anvil-state.json` |
| `cast: command not found` | Foundry no está en tu máquina | `docker compose -f compose/docker-compose.anvil.yml exec anvil cast ...` |
| `port is already allocated` | Quedó el contenedor de la clase 1 o el otro compose | `docker ps`; `docker rm -f servicio-patron` o `make compose-down` |
| `invalid reference format` | `$PROJECT_ID` vacío, con mayúsculas o con `<...>` | `echo "$AR"` y corregí el `export` |
| `syntax error near unexpected token 'newline'` | Copiaste `export PROJECT_ID=<tu-project-id>` literal | Poné tu valor entre comillas, sin `<>` |
| `denied` / `Unauthenticated` en `docker push` o `pull` | Falta `configure-docker` (o lo corriste sin `sudo` y usás `sudo docker`) | `gcloud auth configure-docker ${REGION}-docker.pkg.dev` con el mismo usuario que corre docker |
| `name unknown` en `docker push` | El repositorio no existe en esa región | `gcloud artifacts repositories list --location=$REGION` |
| `docker: 'compose' is not a docker command` | Docker instalado con `apt install docker.io` | `curl -fsSL https://get.docker.com \| sudo sh` |
