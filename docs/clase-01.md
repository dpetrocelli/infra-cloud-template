# Clase 1 — Arquitectura híbrida y cargas stateful sobre Compute Engine

## Qué mirás de este repo

- `app/main.py` y `app/Dockerfile`: el servicio patrón completo, el mismo
  que armaste a mano en el lab de la clase (acá ya envuelto en FastAPI).
- `terraform/modules/vm/startup-script.sh.tpl`: el mismo procedimiento del
  lab (montar el disco, instalar Docker, correr el contenedor con `-v`),
  pero como script de arranque de una VM.

## La idea central

El contenedor es descartable. El estado —el contador de `/data/counter.txt`—
vive en un disco persistente aparte, no en el filesystem del contenedor ni
en el disco de arranque de la VM. Si matás la VM y creás una nueva montando
el mismo disco, el contador sigue donde lo dejaste.

## Para probarlo vos

```bash
docker build -t servicio-patron:v1 app/
docker run -d --name servicio-patron -p 8080:8080 -v $(pwd)/datos:/data servicio-patron:v1
curl localhost:8080/
curl localhost:8080/metrics | grep servicio_patron
```

Matá el contenedor, corré `docker run` de nuevo con el mismo `-v`: el
contador no se resetea.

## Qué es "el repo template" en la práctica

A partir de esta clase, cada vez que veas "desplegá el servicio patrón" en
una clase siguiente, es *este* repo: mismo código, mismo contrato de
endpoints, mismo puerto (8080), misma variable `DATA_DIR`.
