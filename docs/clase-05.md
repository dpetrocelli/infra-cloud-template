# Clase 5: Kubernetes con Helm, Persistent Volumes y StatefulSets

## Objetivo

Llevar el servicio patrón a Kubernetes con Helm y comprobar que **cada réplica
tiene su propio disco** (StatefulSet + PVC) que sobrevive a borrar el pod.
Primero en un cluster local (k3s adentro de Docker, con k3d); después, lo
mismo en GKE.

Al terminar tenés:

1. Un cluster local con las imágenes del repo adentro.
2. `servicio-patron` instalado con Helm, con su PVC `Bound`, y la prueba de que el contador sobrevive a `kubectl delete pod`.
3. BC: Anvil como StatefulSet conservando la cadena. IA: el modelo como Deployment con HPA, upgrade y rollback.
4. (En la nube) lo mismo en GKE con la imagen de Artifact Registry.

## Prerrequisitos

- [ ] `make doctor` muestra `[ok]` en `kubectl`, `helm` y `k3d`.
- [ ] Al menos 10 GB libres y más de 15% de disco libre (si no, el nodo se
      marca con *disk-pressure* y los pods quedan `Pending`; `make doctor` lo avisa).
- [ ] Nada escuchando en 18080 (lo usamos para el port-forward).
- [ ] `make compose-down` si quedó el compose de la clase 3.

## Pasos en tu laptop (k3d)

### 1. Creá el cluster

```bash
make k3d-up            # k3d cluster create infra-cloud --agents 1 --wait
kubectl get nodes
kubectl get storageclass
```

Esperado: 2 nodos `Ready` y la StorageClass `local-path (default)`. k3d
agrega el contexto `k3d-infra-cloud` a tu `~/.kube/config` y lo deja activo.

### 2. Metele las imágenes

k3s no ve las imágenes de tu Docker: hay que copiarlas al cluster.

```bash
make k3d-images        # make build + k3d image import app:local model:local pow:local anvil-exporter:local
```

### 3. Revisá los charts antes de instalar

```bash
make helm-lint
helm template servicio-patron helm/charts/servicio-patron -f helm/charts/servicio-patron/values-k3s.yaml | less
```

Cada chart trae dos archivos de valores:

- `values.yaml`: para GKE (StorageClass por defecto del cluster, imagen de Artifact Registry).
- `values-k3s.yaml`: para tu cluster local (`local-path`, imagen `:local`, `pullPolicy: Never`).

### 4. Instalá el servicio patrón

```bash
helm upgrade --install servicio-patron helm/charts/servicio-patron \
  -f helm/charts/servicio-patron/values-k3s.yaml --wait
kubectl get pods,pvc,svc,hpa
```

Esperado:

```
pod/servicio-patron-0   1/1   Running
persistentvolumeclaim/data-servicio-patron-0   Bound   ...   local-path
service/servicio-patron   ClusterIP   ...   8080/TCP
horizontalpodautoscaler.../servicio-patron   StatefulSet/servicio-patron   cpu: 2%/60%   1   5   1
```

El HPA puede mostrar `cpu: <unknown>/60%` el primer minuto: es normal.

### 5. Probalo

En una **segunda terminal** (queda corriendo):

```bash
kubectl port-forward svc/servicio-patron 18080:8080
```

En la primera:

```bash
curl localhost:18080/
curl localhost:18080/
curl -s -X POST localhost:18080/items -H 'Content-Type: application/json' -d '{"name":"clase5"}'; echo
```

### 6. Borrá el pod

```bash
kubectl delete pod servicio-patron-0
kubectl wait --for=condition=Ready pod/servicio-patron-0 --timeout=120s
```

El port-forward de la otra terminal se corta (`lost connection to pod`): cortalo
con Ctrl+C y lanzalo de nuevo. Después:

```bash
curl localhost:18080/          # Visitas persistidas en disco: 3
curl -s localhost:18080/items; echo
```

El pod es nuevo (mismo nombre, otro UID: `kubectl get pod servicio-patron-0 -o jsonpath='{.metadata.uid}'`),
el PVC es el mismo. Como en la clase 1, `servicio_patron_hits_total` de
`/metrics` vuelve a cero porque vive en memoria.

Para ver dos réplicas con un disco cada una:

```bash
helm upgrade servicio-patron helm/charts/servicio-patron -f helm/charts/servicio-patron/values-k3s.yaml \
  --set autoscaling.enabled=false --set replicaCount=2 --wait
kubectl get pods,pvc -l app=servicio-patron     # servicio-patron-0/-1 y data-servicio-patron-0/-1
```

Con el HPA prendido, `replicaCount` no se usa: las réplicas las decide el HPA,
y el chart no pisa esa decisión en cada `helm upgrade`.

## Pista BC: Anvil como StatefulSet

```bash
helm upgrade --install anvil helm/charts/anvil -f helm/charts/anvil/values-k3s.yaml --wait
kubectl logs anvil-0 | sed -n '/Available Accounts/,/Wallet/p' | head -8   # cuentas y claves de prueba
KEY0=0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80
ACC1=0x70997970C51812dc3A010C7d01b50e0d17dc79C8
kubectl exec anvil-0 -- cast send --private-key $KEY0 --value 1ether $ACC1
kubectl exec anvil-0 -- cast block-number                  # 1
kubectl delete pod anvil-0 && kubectl wait --for=condition=Ready pod/anvil-0 --timeout=120s
kubectl exec anvil-0 -- cast block-number                  # sigue en 1
kubectl exec anvil-0 -- cast balance $ACC1 --ether         # 10001
```

`cast` viene en la imagen de Foundry, así que corre adentro del pod: no hace
falta instalar nada. El chart pone `fsGroup: 1000` (Anvil no corre como root) y
`--state-interval 5`: aunque el pod muera de golpe (OOM, nodo caído) se pierden
a lo sumo 5 segundos. Lo probamos con `kubectl delete pod anvil-0 --grace-period=0 --force`.

El nodo PoW (`helm/charts/pow`) es el caso de la clase 8; si querés mirarlo hoy:
`helm upgrade --install pow helm/charts/pow -f helm/charts/pow/values-k3s.yaml --wait`
y `kubectl get pods -l app=pow -w` (arranca con 1 pod y el HPA lo sube a 3).

## Pista IA: el modelo como Deployment con HPA

El modelo no tiene estado propio (los pesos están en la imagen), así que es un
Deployment sin PVC.

```bash
helm upgrade --install model helm/charts/model -f helm/charts/model/values-k3s.yaml --wait
kubectl get deploy,hpa model          # el HPA lo sube a 2 réplicas en unos segundos
kubectl port-forward svc/model 18081:8081     # en otra terminal
curl -s -X POST localhost:18081/predict -H 'Content-Type: application/json' -d '{"features":[5.1,3.5,1.4,0.2]}'; echo
```

Upgrade y rollback:

```bash
helm upgrade model helm/charts/model -f helm/charts/model/values-k3s.yaml --set autoscaling.minReplicas=3 --wait
kubectl get hpa model                 # MINPODS 3
helm history model
helm rollback model 1 --wait
```

Cuando un chart cambia entre clases, usá `-f` con los mismos valores (como
arriba) o `--reset-then-reuse-values`; `--reuse-values` solo ignora las claves
nuevas del chart.

> ### En la nube (GKE)
>
> 1. En `terraform/envs/dev/dev.tfvars` poné `enable_gke = true` y aplicá
>    (clase 2). Son unos 10 minutos y **cuesta plata mientras existe**.
> 2. `tofu output gke_get_credentials` te da el comando para apuntar `kubectl`
>    al cluster (`gcloud container clusters get-credentials infra-cloud-dev-gke --zone southamerica-east1-a ...`).
>    Si pide un plugin: `gcloud components install gke-gcloud-auth-plugin`.
> 3. Instalá con `values.yaml` (sin el `-f values-k3s.yaml`) y la imagen de la clase 3:
>
> ```bash
> helm upgrade --install servicio-patron helm/charts/servicio-patron \
>   --set image.repository="$AR/app" --set image.tag=v1 --wait
> kubectl get pvc     # StorageClass standard-rwo (un Persistent Disk)
> ```
>
> BC: `helm upgrade --install anvil helm/charts/anvil --wait` (la imagen es pública).
> IA: `helm upgrade --install model helm/charts/model --set image.repository="$AR/model" --set image.tag=v1 --wait`.
>
> Al terminar: `helm uninstall ...`, `kubectl delete pvc --all` y
> `enable_gke = false` + `tofu apply` para borrar el cluster.

## Limpieza

```bash
helm uninstall --ignore-not-found servicio-patron anvil model pow
kubectl get pvc                 # los PVC NO se borran con helm uninstall (a propósito)
kubectl delete pvc --all        # ahora sí se pierden los datos
make k3d-down                   # borra el cluster entero
```

## Errores frecuentes

| Si ves | Causa | Hacé |
|---|---|---|
| Pod y PVC en `Pending`, y `kubectl describe pvc` dice `storageclass "standard" not found` | Instalaste con valores de GKE en k3s | `helm uninstall`, `kubectl delete pvc -l app=<chart>` e instalá con `-f values-k3s.yaml` |
| `UPGRADE FAILED: ... updates to statefulset spec for fields other than 'replicas' ... are forbidden` | Cambiaste la StorageClass, el tamaño o `PEERS` de un StatefulSet existente | `helm uninstall <release>`, `kubectl delete pvc -l app=<release>` y reinstalá |
| `ErrImageNeverPull` | La imagen `:local` no está en el cluster | `make k3d-images` |
| `ErrImagePull` / `ImagePullBackOff` en GKE | `image.repository` o el tag no existen en Artifact Registry | `--set image.repository=$AR/app --set image.tag=v1`; revisá `gcloud artifacts docker images list $AR` |
| Pods `Pending` con `node(s) had untolerated taint {node.kubernetes.io/disk-pressure}` | Disco de tu máquina casi lleno | `docker system prune`; como último recurso, recreá el cluster con el `K3D_ARGS` que explica el `Makefile` |
| `error: lost connection to pod` | El pod del port-forward se borró o se reemplazó | Volvé a lanzar el `kubectl port-forward` |
| `bind: address already in use` en el port-forward | Ya hay otro port-forward o un contenedor en ese puerto | `jobs` / `kill %1`, o usá otro puerto local (`18082:8080`) |
| `422` en `POST /items` | El campo es `name` | `-d '{"name":"clase5"}'` |
| El HPA muestra `<unknown>` | metrics-server todavía no tiene datos | Esperá un minuto |
| El HPA sube réplicas sin carga, recién instalado | El arranque de Python consume CPU | Esperá ~5 minutos (ventana de estabilización) antes de medir la línea base |
| `helm install` devuelve OK pero los pods siguen `Pending` | Sin `--wait`, helm no espera | Usá `--wait` y mirá `kubectl get pods` |
