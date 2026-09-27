# Clase 6 — Observabilidad: Cloud Monitoring, Prometheus, Grafana y Loki

## Qué mirás de este repo

- `observability/kube-prometheus-stack-values.yaml`: valores mínimos para
  instalar Prometheus + Grafana en el cluster de la clase 5.
- `observability/loki-values.yaml`: idem para Loki (logs).
- `observability/servicemonitors.yaml`: un `ServiceMonitor` por servicio,
  para que Prometheus sepa qué scrapear.
- `observability/dashboards/*.json`: un dashboard de Grafana por servicio
  (`servicio-patron`, `anvil`, `pow`, `model`).
- `observability/anvil-exporter/`: Anvil habla JSON-RPC, no Prometheus. Este
  exporter de ~40 líneas traduce `eth_blockNumber` a una métrica.

## Todos los servicios ya exponen `/metrics`

Desde `app/`, `model/` y `pow/` hasta el exporter de Anvil: todos hablan el
formato de exposición de Prometheus desde el día 1. Nada que agregar acá,
sólo conectar Prometheus a scrapearlos.

## Para probarlo vos

```bash
docker compose -f compose/docker-compose.yml up -d --build
curl localhost:8080/metrics
```

En un cluster real:

```bash
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm install kube-prom prometheus-community/kube-prometheus-stack \
  -f observability/kube-prometheus-stack-values.yaml
kubectl apply -f observability/servicemonitors.yaml
```

Los dashboards de `observability/dashboards/` se auto-cargan si los subís
como `ConfigMap` etiquetado `grafana_dashboard=1` (el sidecar de Grafana ya
está habilitado en `kube-prometheus-stack-values.yaml`).

## Qué mirar primero ante un incidente

Métricas → te dicen *que* algo anda mal (una tasa de error, una latencia).
Logs (Loki) → te dicen *por qué*. Cada dashboard acá arranca por la métrica
que más rápido te avisa: `servicio_patron_hits_total`, `pow_block_height`,
`anvil_block_number`, `model_predictions_total`.
