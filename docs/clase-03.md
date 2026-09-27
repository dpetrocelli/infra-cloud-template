# Clase 3 — Contenedores con Docker y Artifact Registry

## Qué mirás de este repo

- `app/Dockerfile`, `model/Dockerfile`, `pow/Dockerfile`: tres imágenes
  chicas, cada una con un único proceso y un único puerto.
- `terraform/modules/artifact-registry/`: el repositorio Docker gestionado
  donde termina viviendo cada imagen (ver clase 4).
- `compose/docker-compose.yml`: el servicio patrón corriendo con su volumen.
- `compose/docker-compose.anvil.yml` (ejemplo Blockchain): Anvil + servicio
  patrón, con Anvil guardando su estado en disco vía `--state`.

## La idea central

"En mi máquina anda" se resuelve empaquetando el runtime completo (código +
dependencias) en una imagen. Compará el tamaño de las tres imágenes: son
chicas a propósito (`python:3.12-slim`, sin capas de más).

## Para probarlo vos

```bash
docker build -t servicio-patron:local app/
docker images servicio-patron:local   # mirá el tamaño

docker compose -f compose/docker-compose.yml up -d --build
curl localhost:8080/

# Ejemplo Blockchain: Anvil con estado persistente
docker compose -f compose/docker-compose.anvil.yml up -d --build
curl -X POST -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"eth_blockNumber","params":[],"id":1}' \
  localhost:8545
```

## Achicar la imagen

Fijate en cada `Dockerfile`: una sola etapa, base `-slim`, `--no-cache-dir`
en el `pip install`. Para el modelo (`model/Dockerfile`) los pesos se
entrenan *durante* el build (`RUN python train.py`), no se descargan en cada
arranque del contenedor.
