# Clase 5 — Kubernetes con GKE: Helm, Persistent Volumes y StatefulSets

## Qué mirás de este repo

- `terraform/modules/gke/`: un cluster GKE chico, zonal (un solo control
  plane, más barato que uno regional), con nodos `e2-small`.
- `helm/charts/servicio-patron/`: `StatefulSet` + `PersistentVolumeClaim`
  por réplica + `Service` + `HorizontalPodAutoscaler`.
- `helm/charts/anvil/` (ejemplo Blockchain): mismo patrón para Anvil, con un
  sidecar exporter chiquito (ver clase 6).
- `helm/charts/model/` (ejemplo IA): acá sí es un `Deployment` común, porque
  el modelo no tiene estado propio (los pesos van adentro de la imagen).

## StatefulSet vs Deployment: cuándo cada uno

Un `Deployment` no te garantiza qué pod usa qué volumen si escalás — sirve
para lo que no tiene estado (el `model/`). Un `StatefulSet` le da a **cada
réplica** su propio `PersistentVolumeClaim`, con una identidad de red
estable (`pod-0`, `pod-1`, ...). El servicio patrón y Anvil son stateful:
necesitan `StatefulSet`.

## Para probarlo vos

```bash
for c in servicio-patron anvil pow model; do
  helm lint helm/charts/$c
  helm template test helm/charts/$c | head -30
done
```

(`helm template` no necesita un cluster real: sólo renderiza los manifests
para que los revises antes de aplicarlos.)

## Sobre `pow/` y las StatefulSets peereadas

El chart `helm/charts/pow` levanta **N réplicas** con un *headless service*
(`clusterIP: None`), que le da a cada pod un nombre DNS estable
(`pow-0.pow-headless`, `pow-1.pow-headless`, ...). Así arman su lista de
`PEERS` sin necesitar descubrimiento externo. Esto se usa recién en la
clase 8, pero el chart ya está listo desde acá.
