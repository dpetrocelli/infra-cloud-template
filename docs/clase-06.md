# Clase 6: Observabilidad con Prometheus, Grafana y Loki

## Objetivo

Que tus servicios se puedan **mirar**: métricas en Prometheus, logs en Loki y
las dos cosas en Grafana. Las métricas te dicen *que* algo anda mal; los logs,
*por qué*.

```
pods (/metrics) ──ServiceMonitor──> Prometheus ──┐
                                                 ├──> Grafana (dashboards, alertas)
pods (stdout) ──Alloy──> Loki ───────────────────┘
```

Al terminar tenés:

1. kube-prometheus-stack, Loki y Alloy instalados en el namespace `observability`.
2. Los targets de tus servicios en `UP` y los dashboards del repo cargados.
3. Una consulta LogQL que encuentra tus errores.
4. BC: la altura de bloque de Anvil como métrica. IA: latencia y réplicas del modelo bajo carga.

## Prerrequisitos

- [ ] El cluster de la clase 5 (`make k3d-up && make k3d-images`) con el
      servicio patrón instalado con el release `servicio-patron`.
- [ ] Unos 3 GB de RAM libres para el stack.
- [ ] Puertos locales 19090, 13000 y 18080 libres.

## Pasos

### 1. Repositorios de Helm y contraseña de Grafana

```bash
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo add grafana https://grafana.github.io/helm-charts
helm repo update
export GRAFANA_PASS='elegí-una'     # no la commitees
```

### 2. Prometheus + Grafana

```bash
helm upgrade --install kube-prom prometheus-community/kube-prometheus-stack \
  --version 91.9.0 -n observability --create-namespace \
  -f observability/kube-prometheus-stack-values.yaml \
  --set grafana.adminPassword="$GRAFANA_PASS" --wait --timeout 8m
kubectl get pods -n observability
```

Esperado: pods de `grafana`, `kube-prometheus-stack-operator`,
`kube-state-metrics`, `prometheus-node-exporter` y `prometheus-kube-prom-...`
en `Running`. **No hay Alertmanager**: está apagado a propósito (las alertas
las hacemos en Grafana).

Las versiones están fijadas (`--version`): son las que probamos. Sin eso, un
chart nuevo puede cambiar el formato de los valores (le pasó a Loki).

### 3. Decile a Prometheus qué scrapear

```bash
kubectl apply -f observability/servicemonitors.yaml
kubectl -n observability port-forward svc/kube-prom-kube-prometheus-prometheus 19090:9090
```

(El port-forward en otra terminal.) Abrí `http://localhost:19090/targets`:
`serviceMonitor/default/servicio-patron/0` tiene que estar `UP`. Los
ServiceMonitors eligen los Services por la etiqueta `app.kubernetes.io/name`
que pone cada chart, así que funcionan con cualquier nombre de release y en
cualquier namespace.

En `http://localhost:19090/graph` probá `up{job="servicio-patron"}` (tiene que
dar 1) y `rate(servicio_patron_hits_total[1m])`.

### 4. Grafana y los dashboards del repo

```bash
for f in observability/dashboards/*.json; do
  kubectl create configmap "dash-$(basename "$f" .json)" -n observability --from-file="$f" \
    --dry-run=client -o yaml | kubectl label --local -f - grafana_dashboard=1 -o yaml | kubectl apply -f -
done
kubectl -n observability port-forward svc/kube-prom-grafana 13000:80
```

Entrá a `http://localhost:13000` con `admin` y tu `$GRAFANA_PASS`. Si no la
pasaste al instalar, el chart generó una al azar:
`kubectl -n observability get secret kube-prom-grafana -o jsonpath='{.data.admin-password}' | base64 -d; echo`.

En **Dashboards** aparecen `Servicio patron`, `Model server`, `Mini PoW
baseline` (solo la altura de bloque; los paneles de tu red los agregás en el
TF) y `Anvil (BC dev chain)`. El del servicio patrón trae tres paneles (requests/s,
items/s, latencia p95 por path). Generá tráfico para verlos moverse:

```bash
kubectl port-forward svc/servicio-patron 18080:8080      # otra terminal
for i in $(seq 1 200); do curl -s -o /dev/null localhost:18080/; done
```

### 5. Logs: Loki + Alloy

```bash
helm upgrade --install loki grafana/loki --version 7.3.0 -n observability \
  -f observability/loki-values.yaml --wait --timeout 6m
helm upgrade --install alloy grafana/alloy --version 1.13.0 -n observability \
  --set controller.type=deployment \
  --set-file alloy.configMap.content=observability/alloy-logs.alloy --wait
kubectl get pods -n observability -l app.kubernetes.io/name=loki
```

Alloy lee los logs de todos los pods por la API de Kubernetes y los manda a
Loki con las etiquetas `app` y `namespace`. Grafana ya tiene el data source
`Loki` (lo declara `kube-prometheus-stack-values.yaml`).

Generá un error y buscalo:

```bash
for i in $(seq 1 20); do curl -s -o /dev/null localhost:18080/no-existe; done
```

En Grafana → **Explore** → data source **Loki**:

```
{app="servicio-patron"} |= "404"
```

Esperado: las líneas `GET /no-existe HTTP/1.1" 404 Not Found`. Buscá `404`, no
`error`: el servicio no escribe la palabra "error" en una respuesta 404.

### 6. Una alerta (en Grafana)

**Alerting → Alert rules → New alert rule**, consulta Prometheus
`up{job="servicio-patron"}`, condición `IS BELOW 1`, evaluación cada 1m.
Para dispararla: `kubectl scale statefulset servicio-patron --replicas=0` (el
HPA la vuelve a subir en unos minutos; para que no lo haga, primero
`kubectl delete hpa servicio-patron`).

## Pista BC: métricas de Anvil

Anvil habla JSON-RPC, no Prometheus. `observability/anvil-exporter/` es un
traductor de 40 líneas que publica `anvil_block_number`.

```bash
make k3d-images      # incluye anvil-exporter:local
helm upgrade --install anvil helm/charts/anvil -f helm/charts/anvil/values-k3s.yaml \
  --set exporter.enabled=true --wait
kubectl get pod anvil-0        # 2/2: anvil + exporter
kubectl exec anvil-0 -c anvil -- cast rpc evm_mine
```

En Prometheus, `anvil_block_number` sube con cada `evm_mine` (o con cada
transacción). Con dos contenedores en el pod, `kubectl exec` y `kubectl logs`
necesitan `-c anvil`. Sin tráfico Anvil no mina (automine), así que una alerta
de "bloque sin avanzar" se dispara sola: agregá `--block-time` o tenela en cuenta.

## Pista IA: el modelo bajo carga

```bash
helm upgrade --install model helm/charts/model -f helm/charts/model/values-k3s.yaml --wait
kubectl create configmap k6-script --from-file=loadtest/k6-script.js --dry-run=client -o yaml | kubectl apply -f -
kubectl delete job k6 --ignore-not-found
kubectl apply -f loadtest/k6-job.yaml       # TARGET=model, SLEEP=0.05
kubectl get hpa model -w                    # Ctrl+C para salir
```

El dashboard `Model server` muestra predicciones/s, latencia p95 y las réplicas
del HPA. La carga se genera **adentro del cluster**: un port-forward manda todo
a un solo pod y las réplicas nuevas no reciben tráfico.

Las métricas del modelo son `model_predictions_total` y el histograma
`model_predict_seconds`. Si querés una métrica propia (por ejemplo la
confianza), agregala en `model/serve.py` con `prometheus_client`.

> ### En la nube (GKE)
>
> Los mismos comandos sirven contra el cluster de GKE de la clase 5 (con
> `kubectl` apuntando ahí). Diferencias: los PVC usan `standard-rwo` (Persistent
> Disk) y conviene nodos con más memoria que `e2-small` para todo el stack. GCP
> trae además **Cloud Monitoring** y **Managed Service for Prometheus**: es la
> alternativa administrada a instalar kube-prometheus-stack vos.

## Limpieza

```bash
helm uninstall alloy loki kube-prom -n observability
kubectl delete -f observability/servicemonitors.yaml
kubectl delete pvc --all -n observability
kubectl delete namespace observability
kubectl get crd -o name | grep monitoring.coreos.com | xargs kubectl delete    # opcional: CRDs del operador
```

## Errores frecuentes

| Si ves | Causa | Hacé |
|---|---|---|
| `You have more than zero replicas configured for both the single binary and simple scalable targets` | Valores viejos de Loki | Usá `observability/loki-values.yaml` del repo |
| `You must provide a schema_config for Loki` | Idem | Idem |
| Pods `chunks-cache` en `Pending` pidiendo ~10 GiB | Idem (memcached) | Idem: el archivo los apaga |
| `401` al entrar a Grafana | Contraseña equivocada (no es `prom-operator`) | `kubectl -n observability get secret kube-prom-grafana -o jsonpath='{.data.admin-password}' \| base64 -d` |
| No aparece el data source Loki | Instalaste kube-prom sin el archivo de valores del repo | `helm upgrade` de kube-prom con `-f observability/kube-prometheus-stack-values.yaml` |
| El target no aparece en `/targets` | No aplicaste los ServiceMonitors, o tu Service no tiene `app.kubernetes.io/name` | `kubectl apply -f observability/servicemonitors.yaml`; `kubectl get svc --show-labels` |
| `{app="servicio-patron"} \|= "error"` no trae nada | El servicio loguea `404 Not Found`, no "error" | Buscá `\|= "404"` |
| `kubectl get pods -l app=loki` no encuentra nada | La etiqueta del chart es otra | `-l app.kubernetes.io/name=loki` |
| `anvil-0` en `ErrImageNeverPull` | La imagen del exporter no está en el cluster | `make k3d-images` |
| `kubectl exec anvil-0 -- cast ...` dice `container not found` o entra al exporter | El pod tiene dos contenedores | `kubectl exec anvil-0 -c anvil -- cast ...` |
| Pods `Pending` con disk-pressure | Disco de tu máquina casi lleno | Ver la clase 5 |
