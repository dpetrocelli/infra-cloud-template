# Clase 1: Arquitectura híbrida y cargas stateful sobre Compute Engine

## Objetivo

Ver con tus propios ojos que **el contenedor es descartable y el estado no**.
El servicio patrón cuenta visitas en `/data/counter.txt`. Si `/data` es un
disco aparte, podés borrar el contenedor (o la VM entera) y el contador sigue
donde estaba. Primero lo hacés en tu laptop; después, lo mismo en una VM de
GCP con un disco persistente.

Al terminar tenés:

1. El servicio patrón corriendo en tu laptop con el estado en `./datos`.
2. La prueba de que sobrevive a recrear el contenedor (y de que sin disco se pierde).
3. El mismo esquema en una VM de Compute Engine con el disco en `/mnt/disks/datos`
   (los entregables exactos están en el lab de Moodle).

## Prerrequisitos

- [ ] Tu copia del repo clonada y `make doctor` sin `[FAIL]` (ver el
      [README](../README.md#primeros-10-minutos)).
- [ ] Estás parado en la **raíz del repo** (`ls` muestra `app/ Makefile README.md`).
- [ ] El puerto 8080 está libre (`make doctor` lo chequea).

## Pasos en tu laptop

### 1. (Opcional) Corré los tests del servicio

```bash
make test-app
```

Esperado: `4 passed`.

### 2. Construí la imagen

```bash
docker build -t app:local app/
docker images app:local
```

Esperado: una imagen de unos 250 MB. Si ves `path "app/" not found`, no
estás en la raíz del repo.

### 3. Corré el contenedor con el estado en un directorio tuyo

```bash
mkdir -p datos
docker run -d --name servicio-patron -p 8080:8080 \
  -v "$PWD/datos:/data" --user "$(id -u):$(id -g)" app:local
until curl -sf localhost:8080/healthz; do sleep 1; done; echo
```

- `-v "$PWD/datos:/data"` monta tu carpeta `datos/` como `/data` del contenedor.
- `--user "$(id -u):$(id -g)"` hace que los archivos queden a tu nombre (si no,
  en Linux quedan de root y después no los podés borrar).
- El `until` espera a que el servicio conteste (tarda alrededor de un segundo).

Esperado: `{"status":"ok"}`.

### 4. Generá estado

```bash
curl localhost:8080/
curl localhost:8080/
curl -s -X POST localhost:8080/items -H 'Content-Type: application/json' -d '{"name":"gpu","value":"t4"}'; echo
cat datos/counter.txt; echo
curl -s localhost:8080/metrics | grep '^servicio_patron_hits_total'
```

Esperado:

```
Servicio patron activo. Visitas persistidas en disco: 1
Servicio patron activo. Visitas persistidas en disco: 2
{"name":"gpu","value":"t4","created_at":...}
2
servicio_patron_hits_total 2.0
```

### 5. Borrá el contenedor y creá otro con el mismo disco

```bash
docker rm -f servicio-patron
docker run -d --name servicio-patron -p 8080:8080 \
  -v "$PWD/datos:/data" --user "$(id -u):$(id -g)" app:local
until curl -sf localhost:8080/healthz; do sleep 1; done; echo
curl localhost:8080/
curl -s localhost:8080/items; echo
```

Esperado: `Visitas persistidas en disco: 3` y el item `gpu` sigue ahí. El
contenedor es nuevo, el estado no.

Ojo: `servicio_patron_hits_total` en `/metrics` vuelve a empezar, porque esa
métrica vive en memoria. El contador del disco no. Es a propósito (lo vemos en
la clase 6).

### 6. Contraprueba: sin disco, el estado se pierde

```bash
docker rm -f servicio-patron
docker run -d --name sin-disco -p 8080:8080 app:local
until curl -sf localhost:8080/healthz; do sleep 1; done; echo
curl localhost:8080/
docker rm -f sin-disco
```

Esperado: `Visitas persistidas en disco: 1`. Sin `-v`, `/data` vive adentro del
contenedor y muere con él.

## Pista BC: Anvil con estado en disco

Anvil (la blockchain local de Foundry) guarda su estado con `--state`. Para que
eso funcione de verdad hacen falta tres cosas (en la clase 3 las vas a ver
resueltas en `compose/docker-compose.anvil.yml`):

1. El directorio tiene que ser del uid 1000 (Anvil no corre como root).
2. `--entrypoint anvil`, así Anvil recibe la señal de stop y guarda al salir.
3. `--state-interval 5`, así también guarda cada 5 segundos (por si lo matan).

```bash
mkdir -p datos-anvil
docker run -d --name anvil -p 8545:8545 -v "$PWD/datos-anvil:/state" \
  --user "$(id -u):$(id -g)" --entrypoint anvil ghcr.io/foundry-rs/foundry:stable \
  --host 0.0.0.0 --state /state/anvil-state.json --state-interval 5
sleep 3
docker exec anvil cast rpc evm_mine >/dev/null
docker exec anvil cast block-number
docker stop anvil && docker rm anvil     # stop (no rm -f): Anvil guarda al salir
ls datos-anvil/                           # tiene que aparecer anvil-state.json
```

Volvé a correr el mismo `docker run` y `docker exec anvil cast block-number`
tiene que seguir en `1`. Limpieza: `docker rm -f anvil && rm -r datos-anvil`.

## Pista IA: inferencia con estado afuera

El servidor de `model/` no tiene estado propio: los pesos viajan adentro de la
imagen (clase 3 y 7). Lo que sí aplica hoy es la regla: **todo lo que tenga que
sobrevivir (pesos descargados, caché de modelos, resultados) va a un disco
montado**, no al filesystem del contenedor. Si en el lab usás Ollama, montá su
directorio de modelos en el disco de datos (`-v /mnt/disks/datos/ollama:/root/.ollama`)
y usá una VM **e2-medium** o más grande: `llama3.2:1b` ocupa alrededor de
1,5 GB de RAM y en una e2-small (2 GB) no entra junto con el servicio patrón.

> ### En la nube (Compute Engine)
>
> Lo mismo que hiciste en la laptop, con un disco persistente de GCP en lugar
> de `./datos`. El lab de Moodle tiene la versión paso a paso con la consola;
> estos son los comandos equivalentes.
>
> ```bash
> export PROJECT_ID="mi-proyecto-123" ZONE="southamerica-east1-a"
> gcloud config set project "$PROJECT_ID"
> gcloud compute disks create servicio-patron-datos --size=10GB --type=pd-balanced --zone="$ZONE"
> gcloud compute instances create vm-servicio-patron --zone="$ZONE" --machine-type=e2-small \
>   --image-family=debian-12 --image-project=debian-cloud --tags=app-server \
>   --disk=name=servicio-patron-datos,device-name=datos,mode=rw,boot=no
> gcloud compute firewall-rules create allow-servicio-patron --allow=tcp:8080 --target-tags=app-server
> gcloud compute ssh vm-servicio-patron --zone="$ZONE"
> ```
>
> Adentro de la VM:
>
> ```bash
> DEV=/dev/disk/by-id/google-datos        # nombre estable del disco (no /dev/sdb)
> sudo blkid "$DEV" || sudo mkfs.ext4 -F "$DEV"   # formatea SOLO si es nuevo
> sudo mkdir -p /mnt/disks/datos
> grep -q /mnt/disks/datos /etc/fstab || echo "$DEV /mnt/disks/datos ext4 discard,defaults,nofail 0 2" | sudo tee -a /etc/fstab
> sudo mount -a && mountpoint /mnt/disks/datos
> curl -fsSL https://get.docker.com | sudo sh
> sudo apt-get install -y git
> git clone https://github.com/<tu-usuario>/<tu-repo>.git && cd <tu-repo>
> sudo docker build -t app:local app/
> sudo docker run -d --name servicio-patron --restart unless-stopped -p 8080:8080 \
>   -v /mnt/disks/datos:/data app:local
> ```
>
> Desde tu laptop: `curl http://<IP-externa>:8080/` (la IP está en
> `gcloud compute instances list`). Para probar que el estado sobrevive a la VM:
> borrá la VM (`gcloud compute instances delete vm-servicio-patron`, el disco
> queda), creá otra con el mismo `--disk=...` y repetí los pasos de adentro
> **sin el `mkfs`** (el `blkid` lo evita solo). El código fuente vivía en el
> disco de arranque, así que lo volvés a clonar.
>
> `/dev/disk/by-id/google-datos` es lo mismo que el lab llama "montar por
> nombre estable": `datos` es el `device-name` que le diste al disco. Es lo que
> usa también `terraform/modules/vm/startup-script.sh.tpl` en la clase 2.
>
> Sin GCP todavía, podés validar ese módulo offline:
> `cd terraform/modules/vm && tofu init -backend=false && tofu validate`
> (esperado: `Success! The configuration is valid.`).

## Limpieza

```bash
docker rm -f servicio-patron sin-disco 2>/dev/null
rm -r datos            # si te dice Permission denied: sudo rm -r datos
```

En GCP: `gcloud compute instances delete vm-servicio-patron --zone="$ZONE"` y,
cuando ya no lo necesites, `gcloud compute disks delete servicio-patron-datos --zone="$ZONE"`
(el disco se cobra aunque no tenga VM).

## Errores frecuentes

| Si ves | Causa | Hacé |
|---|---|---|
| `Conflict. The container name "/servicio-patron" is already in use` | El contenedor anterior sigue existiendo (aunque esté parado) | `docker rm -f servicio-patron` y repetí el `docker run` |
| `curl: (56) Recv failure: Connection reset by peer` | El servicio todavía está arrancando | Esperá con `until curl -sf localhost:8080/healthz; do sleep 1; done` |
| `port is already allocated` | Otro contenedor usa el 8080 | `docker ps`, borralo o usá `-p 18080:8080` y `curl localhost:18080/` |
| `rm: cannot remove 'datos/counter.txt': Permission denied` | Corriste sin `--user` y los archivos quedaron de root | `sudo rm -r datos` |
| `500 Internal Server Error` y en `docker logs` un `PermissionError` | `/data` no es escribible para el usuario del contenedor | Usá `--user "$(id -u):$(id -g)"` con un `datos/` creado por vos, o `sudo chown -R 1000:1000` del directorio |
| `path "app/" not found` | No estás en la raíz del repo | `cd` a la carpeta del repo |
| El contador volvió a 1 | Te olvidaste el `-v` o lo montaste en otro path | Revisá `docker inspect servicio-patron --format '{{json .Mounts}}'` |
| `Cannot connect to the Docker daemon` | Docker no corre | Abrí Docker Desktop o `sudo systemctl start docker` |
| En la VM, `docker: command not found` | Todavía no instalaste Docker (o el startup script no terminó) | `curl -fsSL https://get.docker.com \| sudo sh` |
| Anvil volvió al bloque 0 | El directorio no era del uid 1000, o usaste `docker rm -f` sin `--state-interval` | Seguí los tres puntos de la pista BC |
