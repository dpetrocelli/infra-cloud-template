# Clase 8: Caso integrador, de git push a producción

## Objetivo

Conectar todo lo que construiste: un commit pasa por CI (clase 4), queda como
imagen versionada en Artifact Registry (clase 3), Terraform asegura la
infraestructura (clase 2), Helm la despliega en Kubernetes (clase 5), Grafana
la muestra (clase 6) y una prueba de carga hace escalar el HPA.

```
git push ─> ci.yml (test, build, publish :sha) ─> Artifact Registry
                                                        │
Run workflow "deploy" (image_tag=<sha>) ─> terraform ─> GKE ─> helm upgrade ─> pods + HPA
                                                                    │
                                     k6 (Job en el cluster) ─> carga ─> Grafana
```

Al terminar tenés:

1. Un **ensayo completo en tu laptop** (k3d): despliegue, verificación, carga y escalado.
2. BC: una red de nodos PoW que mina y converge. IA: el modelo escalando de 2 a más réplicas.
3. (En la nube) el mismo flujo con `deploy.yml` contra GKE.

## Prerrequisitos

- [ ] Clases 4, 5 y 6 hechas (o al menos `make doctor` con `kubectl`, `helm` y `k3d` en `[ok]`).
- [ ] ~10 GB y más de 15% de disco libre; ~4 GB de RAM para el cluster con observabilidad.

## Ensayo local (k3d)

### 1. Tests e imágenes

```bash
make test
make k3d-up
make k3d-images
```

### 2. Observabilidad

Los mismos pasos 1 a 4 de la [clase 6](clase-06.md) (kube-prometheus-stack,
ServiceMonitors y dashboards). Loki es opcional hoy.

### 3. Desplegá tu pista

BC:

```bash
helm upgrade --install pow helm/charts/pow -f helm/charts/pow/values-k3s.yaml --wait
kubectl get pods,pvc,hpa -l app=pow -w      # Ctrl+C cuando haya 3 pods Running
```

IA:

```bash
helm upgrade --install model helm/charts/model -f helm/charts/model/values-k3s.yaml --wait
kubectl get deploy,hpa model -w             # Ctrl+C cuando haya 2 réplicas
```

Sin el HPA el chart pondría las réplicas fijas; con el HPA prendido no las
pone (si no, cada `helm upgrade` pisaría lo que decidió el HPA). Por eso una
instalación nueva arranca con **1 pod** y en unos segundos el HPA la lleva a
`minReplicas` (3 para pow, 2 para model). `helm --wait` vuelve antes: esperá con
el `-w`.

### 4. Verificá

BC, la red de nodos:

```bash
kubectl port-forward pod/pow-0 18090:8090    # otra terminal
curl -s localhost:18090/peers; echo
curl -s -X POST localhost:18090/tx -H 'Content-Type: application/json' -d '{"sender":"ana","to":"beto","amount":1}'; echo
curl -s -X POST localhost:18090/mine | head -c 200; echo
for p in pow-1 pow-2; do
  kubectl exec $p -- python -c "import urllib.request as u; print(u.urlopen(u.Request('http://localhost:8090/peers/sync', method='POST')).read().decode())"
done
```

Esperado: `/peers` lista **6** URLs (`pow-0` … `pow-5`): la lista se arma para
`maxReplicas` del HPA, así los nodos que agregue después también son peers. Los
que todavía no existen se saltean en el sync, y la métrica `pow_peers` muestra
6 (configurados, no vivos). Cada sync responde `{"replaced":true,"height":1,...}`:
`pow-1` y `pow-2` adoptan la cadena de `pow-0` (la de más trabajo acumulado y válida).

Los bloques **no se propagan solos**: cada nodo se entera cuando corre
`/peers/sync`. Si dos nodos minaron cadenas distintas del mismo largo, ninguna
gana (empate) hasta que alguien mine un bloque más; para converger, miná uno en
un nodo y sincronizá los demás.

IA, el modelo:

```bash
kubectl port-forward svc/model 18081:8081    # otra terminal
curl -s -X POST localhost:18081/predict -H 'Content-Type: application/json' -d '{"features":[5.1,3.5,1.4,0.2]}'; echo
```

### 5. Carga y escalado

La carga se genera **adentro del cluster** (un port-forward mandaría todo a un
solo pod):

```bash
kubectl create configmap k6-script --from-file=loadtest/k6-script.js --dry-run=client -o yaml | kubectl apply -f -
kubectl delete job k6 --ignore-not-found
kubectl apply -f loadtest/k6-job.yaml
kubectl get hpa -w
```

`loadtest/k6-job.yaml` viene con `TARGET=model` y `SLEEP=0.05`. Para pow,
editá el archivo: `TARGET=pow` y `SLEEP=1` (cada nodo mina con CPU, alcanza).

Esperado para el modelo: las réplicas pasan de 2 a 4 o más en uno o dos
minutos (lo medimos: 2 → 4 → 6 → 8). Al terminar la carga bajan solas en unos 5
minutos. En Grafana, `Model server` muestra la latencia y las réplicas, y
`Mini PoW blockchain` la altura de cada nodo.

`kubectl logs job/k6` muestra el resumen: `checks` cerca de 100% y
`http_req_failed` debajo de 5%.

### 6. Un cambio y un nuevo deploy

Hacé un cambio visible (BC: un campo nuevo en la respuesta de `/mine`; IA: un
`model_version` en la respuesta de `/predict`), corré `make test`, reconstruí y
actualizá:

```bash
make k3d-images TAG=v2
helm upgrade pow helm/charts/pow -f helm/charts/pow/values-k3s.yaml --set image.tag=v2 --wait     # o model
kubectl rollout status statefulset/pow    # deploy/model para IA
```

Las réplicas que había elegido el HPA se mantienen durante el upgrade.

> ### En la nube (deploy.yml contra GKE)
>
> **Una sola vez**:
>
> ```bash
> export PROJECT_ID="mi-proyecto-123" REGION="southamerica-east1"
> gcloud storage buckets create "gs://${PROJECT_ID}-tfstate" --location="$REGION"   # si no lo creaste en la clase 2
> gcloud services enable container.googleapis.com compute.googleapis.com
> gcloud iam service-accounts create ci-deployer
> DSA="ci-deployer@${PROJECT_ID}.iam.gserviceaccount.com"
> for role in roles/compute.admin roles/container.admin roles/artifactregistry.admin \
>             roles/iam.serviceAccountUser roles/storage.objectAdmin; do
>   gcloud projects add-iam-policy-binding "$PROJECT_ID" --member="serviceAccount:${DSA}" --role="$role"
> done
> # El mismo binding de OIDC de la clase 4, ahora para esta cuenta:
> gcloud iam service-accounts add-iam-policy-binding "$DSA" --role=roles/iam.workloadIdentityUser \
>   --member="principalSet://iam.googleapis.com/projects/<NÚMERO>/locations/global/workloadIdentityPools/github/attribute.repository/<usuario>/<repo>"
> ```
>
> En GitHub:
>
> - Variable `GCP_DEPLOY_SERVICE_ACCOUNT` = `ci-deployer@<proyecto>.iam.gserviceaccount.com`
>   (la de la clase 4 solo puede subir imágenes).
> - Opcional: `GCP_ZONE` (default `southamerica-east1-a`).
> - **Settings → Environments**: `dev` y `prod`. Un *required reviewer* ahí es
>   la aprobación manual, pero solo existe en repos públicos o planes pagos.
>
> **Cada deploy**:
>
> 1. `git push` a `main` y esperá que `ci` publique (el sha está en el log de
>    `publish`: `pushed .../app:<sha>`; o `git rev-parse HEAD`).
> 2. **Actions → deploy → Run workflow**: `env=dev`, `image_tag=<ese sha>` (o
>    `v0.1.0` si creaste el tag). `latest` se rechaza.
> 3. El job `terraform` aplica la red y GKE (`enable_gke=true`); el job `helm`
>    hace `helm upgrade --install --wait` de `servicio-patron`, `model` y `pow`
>    con esa imagen. El primer run tarda ~15 minutos (crear el cluster). En
>    `dev` la imagen también va a la VM de la clase 2: cambiarla **recrea la VM**
>    (el disco de datos es otro recurso y queda).
> 4. `gcloud container clusters get-credentials infra-cloud-dev-gke --zone southamerica-east1-a`
>    y repetí los pasos 4 y 5 de arriba contra GKE (sin `-f values-k3s.yaml`).
>
> **Al terminar**, GKE se cobra por hora: desde `terraform/envs/dev`,
> `tofu destroy -var-file=dev.tfvars -var enable_gke=true` (o al menos
> `enable_gke=false` + `apply`). Los PVC de GKE son discos: borralos antes con
> `kubectl delete pvc --all`.

## Limpieza (local)

```bash
kubectl delete job k6 --ignore-not-found
helm uninstall --ignore-not-found pow model servicio-patron
helm uninstall --ignore-not-found kube-prom loki alloy -n observability
make k3d-down
```

## Errores frecuentes

| Si ves | Causa | Hacé |
|---|---|---|
| PVC `Pending`, `storageclass "standard" not found` | Instalaste con los valores de GKE | `helm uninstall pow`, `kubectl delete pvc -l app=pow`, reinstalá con `-f values-k3s.yaml` |
| `UPGRADE FAILED: ... updates to statefulset spec ... are forbidden` | Cambiaste StorageClass, tamaño o `PEERS` (p. ej. `maxReplicas`) de un release existente | `helm uninstall pow`, `kubectl delete pvc -l app=pow` y reinstalá |
| `422` en `POST /tx` | Falta `-H 'Content-Type: application/json'` o el campo es `sender` (no `from`) | Copiá el curl de arriba |
| `{"replaced":false,...}` en todos los nodos | Empate entre cadenas del mismo largo | Miná un bloque en un nodo y volvé a sincronizar |
| `error: lost connection to pod` | El HPA borró el pod del port-forward al bajar réplicas | Relanzá el port-forward |
| El HPA no pasa de 2 réplicas | Poca carga (k6 por port-forward o `SLEEP=1`) | El Job de k6 con `SLEEP=0.05` |
| El HPA sube sin carga recién instalado | CPU del arranque | Esperá ~5 min antes de medir la línea base |
| HPA `<unknown>` | metrics-server sin datos todavía | Esperá un minuto |
| `publish` skipped en `ci` | Faltan las variables de la clase 4 | Cargalas; no hay imagen para desplegar sin eso |
| `deploy` falla en `terraform init` con `bucket doesn't exist` | No creaste `gs://<proyecto>-tfstate` | El `gcloud storage buckets create` de arriba |
| `deploy` falla con `image_tag must be a git sha or vX.Y.Z` | Pusiste `latest` o nada | El sha que publicó `ci` |
| `ImagePullBackOff` en GKE | Ese tag no existe en Artifact Registry | `gcloud artifacts docker images list $AR --include-tags` |
| `Error 409: already exists` en el plan de `prod` | El registry ya lo creó `dev` | Es el default (`enable_artifact_registry = false` en prod); no lo prendas |
