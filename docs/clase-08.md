# Clase 8 — Caso integrador: de git push a producción

Esta clase no agrega carpetas nuevas: conecta todo lo que ya construiste.

## Ejemplo IA: git push → modelo de IA en producción

1. Un commit dispara `.github/workflows/ci.yml` (clase 4): tests de
   `model/`, build de la imagen, push a Artifact Registry.
2. `.github/workflows/deploy.yml` aplica `terraform/envs/prod` (clase 2):
   red + GKE.
3. El mismo `deploy.yml` hace `helm upgrade` de `helm/charts/model` (clase 5)
   contra ese cluster.
4. Grafana (clase 6, dashboard `observability/dashboards/model.json`)
   muestra `model_predictions_total` y la latencia p95 en vivo.
5. `loadtest/k6-script.js -e TARGET=model` genera tráfico y el
   `HorizontalPodAutoscaler` del chart escala las réplicas.

## Ejemplo Blockchain: git push → mini-blockchain PoW en producción

1. El mismo pipeline de CI (clase 4) construye y publica la imagen de
   `pow/`.
2. `deploy.yml` aplica Terraform (clase 2) y despliega
   `helm/charts/pow` (clase 5) con **varias réplicas**, peereadas entre sí
   vía el headless service (`pow-0.pow-headless`, `pow-1.pow-headless`, ...).
3. Cada nodo corre `POST /peers/sync`: trae la cadena de cada peer, valida
   cada una con `validate_chain()` y se queda con la de mayor trabajo
   acumulado (regla de "cadena más larga y válida" — ver `pow/blockchain.py`).
4. Grafana (`observability/dashboards/pow.json`) muestra altura de bloque
   por nodo, peers configurados y tiempo de minado (p50/p95).
5. `loadtest/k6-script.js -e TARGET=pow` manda transacciones y minas
   bloques con probabilidad baja por iteración; el HPA de `helm/charts/pow`
   escala la API según CPU.

## Para correrlo de punta a punta (localmente, sin nube)

```bash
make compose-up            # o compose-anvil-up para el ejemplo Blockchain
make test                  # pytest de app/, model/, pow/
cd contracts && forge test # ejemplo Blockchain
```

El pipeline completo (`deploy.yml` real, contra GCP) requiere las variables
de repositorio de la clase 4 y una aprobación manual en el entorno de
GitHub — nunca se auto-aplica.
