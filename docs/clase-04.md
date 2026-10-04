# Clase 4: CI/CD con GitHub Actions y OIDC

## Objetivo

Cada push corre los tests y construye las imágenes; cada push a `main` (y cada
tag de release) publica la imagen en Artifact Registry. Sin ninguna clave
guardada: GitHub emite un token de corta duración (OIDC) y GCP confía en él a
través de un Workload Identity Provider.

Al terminar tenés:

1. Un primer run verde (`test` y `build`) con `publish` en gris (skipped).
2. Workload Identity Federation configurado y las variables del repo cargadas.
3. `$AR/app:<sha>` publicado por un push a `main` y `$AR/app:v0.1.0` por un tag.
4. BC: `contracts.yml` corriendo `forge fmt --check` + `forge test` y, con un
   tag, el deploy a Base Sepolia. IA: tu servicio agregado al pipeline.

## Prerrequisitos

- [ ] Tu repo creado con **Use this template** (en un fork las Actions arrancan deshabilitadas).
- [ ] El repositorio `infra-cloud-template` de Artifact Registry de la clase 3, en `southamerica-east1`.
- [ ] `make doctor` sin `[FAIL]`. `gh` (GitHub CLI) es opcional: todo se puede hacer desde la web.

## Pasos

### 1. Lo mismo que corre CI, en tu laptop

```bash
make test        # app 4, model 6, pow 8 (+2 en skip: TODO del TF), exporter 3 y forge 5 tests
make build
```

`make test-contracts` usa la imagen de Foundry si no tenés `forge`: en la
pista IA no hace falta instalar nada.

### 2. Primer push, sin variables

Hacé cualquier cambio chico, `git commit` y `git push`. En la pestaña
**Actions** el workflow `ci` muestra:

- `test (app)`, `test (model)`, `test (pow)`, `test (observability/anvil-exporter)`: verdes.
- `build (app, 8080)`, `build (model, 8081)`, `build (pow, 8090)`: verdes (incluyen un smoke test contra `/healthz`).
- `publish`: **gris, skipped**. Es lo esperado: todavía no cargaste `GCP_PROJECT_ID`.

### 3. Workload Identity Federation (una vez por proyecto)

> ### En la nube (GCP)
>
> Reemplazá `<usuario>/<repo>` por el tuyo, **exacto** (mayúsculas incluidas).
>
> ```bash
> export PROJECT_ID="mi-proyecto-123" REGION="southamerica-east1"
> export GH_REPO="<usuario>/<repo>"
> gcloud services enable iam.googleapis.com iamcredentials.googleapis.com \
>   sts.googleapis.com artifactregistry.googleapis.com --project="$PROJECT_ID"
>
> gcloud iam workload-identity-pools create github --project="$PROJECT_ID" \
>   --location=global --display-name="GitHub Actions"
> gcloud iam workload-identity-pools providers create-oidc github-provider --project="$PROJECT_ID" \
>   --location=global --workload-identity-pool=github \
>   --issuer-uri="https://token.actions.githubusercontent.com" \
>   --attribute-mapping="google.subject=assertion.sub,attribute.repository=assertion.repository" \
>   --attribute-condition="assertion.repository=='${GH_REPO}'"
>
> gcloud iam service-accounts create ci-artifact-writer --project="$PROJECT_ID"
> SA="ci-artifact-writer@${PROJECT_ID}.iam.gserviceaccount.com"
> gcloud artifacts repositories add-iam-policy-binding infra-cloud-template \
>   --project="$PROJECT_ID" --location="$REGION" \
>   --member="serviceAccount:${SA}" --role=roles/artifactregistry.writer
>
> PROJECT_NUMBER=$(gcloud projects describe "$PROJECT_ID" --format='value(projectNumber)')
> gcloud iam service-accounts add-iam-policy-binding "$SA" --project="$PROJECT_ID" \
>   --role=roles/iam.workloadIdentityUser \
>   --member="principalSet://iam.googleapis.com/projects/${PROJECT_NUMBER}/locations/global/workloadIdentityPools/github/attribute.repository/${GH_REPO}"
>
> # El nombre COMPLETO del provider, para la variable GCP_WORKLOAD_IDENTITY_PROVIDER:
> gcloud iam workload-identity-pools providers describe github-provider --project="$PROJECT_ID" \
>   --location=global --workload-identity-pool=github --format='value(name)'
> ```
>
> El último comando imprime algo como
> `projects/123456789012/locations/global/workloadIdentityPools/github/providers/github-provider`
> (con el **número** de proyecto, no el id).
>
> El binding puede tardar unos 5 minutos en propagarse: si el primer `publish`
> falla con `Permission 'iam.serviceAccounts.getAccessToken' denied`, esperá y
> volvé a correr el job.

### 4. Variables del repositorio

En GitHub: **Settings → Secrets and variables → Actions → Variables → New
repository variable**. Son identificadores, no secretos.

| Variable | Valor | De dónde sale |
|---|---|---|
| `GCP_PROJECT_ID` | `mi-proyecto-123` | tu proyecto |
| `GCP_WORKLOAD_IDENTITY_PROVIDER` | `projects/<NÚMERO>/locations/global/workloadIdentityPools/github/providers/github-provider` | el `describe` del paso 3 |
| `GCP_SERVICE_ACCOUNT` | `ci-artifact-writer@mi-proyecto-123.iam.gserviceaccount.com` | el `SA` del paso 3 |
| `GCP_REGION` | `southamerica-east1` | opcional (es el default) |
| `AR_REPOSITORY` | `infra-cloud-template` | opcional (es el default) |

Con `gh`: `gh variable set GCP_PROJECT_ID --body "$PROJECT_ID"` (y así con cada una).

### 5. Push a `main`: imagen con el sha

Hacé otro push. Ahora `publish (app)`, `publish (model)` y `publish (pow)`
corren y terminan con líneas `pushed .../app:<sha de 40 caracteres>`.

```bash
gcloud artifacts docker images list "${REGION}-docker.pkg.dev/${PROJECT_ID}/infra-cloud-template" --include-tags
```

### 6. Tag de release: imagen con la versión

```bash
git tag v0.1.0
git push origin v0.1.0
```

El workflow corre otra vez (por el tag) y publica **también** `:v0.1.0`. Los
tags tienen que ser `vMAJOR.MINOR.PATCH`; `v1` o `vprueba` se rechazan a
propósito (lo decide `scripts/compute-tags.sh`). No hay `:latest`.

Si querés poner una versión a una imagen ya publicada sin rebuild:
`gcloud artifacts docker tags add "$AR/app:<sha>" "$AR/app:v0.1.1"`.

## Pista BC: el pipeline de contratos

`contracts.yml` corre en cada PR o push a `main` que toque `contracts/`:

```bash
cd contracts && forge fmt --check && forge test -vv && cd ..
# o, sin Foundry instalado:
make test-contracts
```

Esperado: `5 tests passed`. Si `forge fmt --check` falla, corré `forge fmt`
y commiteá.

El deploy a testnet corre **solo con un tag `v*`**. Antes del primer tag:

1. **Settings → Environments → New environment** `testnet`.
2. Adentro, *secret* `BASE_SEPOLIA_DEPLOYER_KEY`: la clave privada de una
   cuenta **solo de testnet** (con o sin `0x`, las dos sirven).
3. Adentro, *variable* `BASE_SEPOLIA_RPC_URL`: `https://sepolia.base.org`.
4. Cargale ETH de prueba a esa cuenta con un faucet (clase 7).

Después: `git tag v0.1.0 && git push origin v0.1.0` → job `deploy-testnet` →
artifact `contracts-v0.1.0` con el ABI, el bytecode y el registro del deploy.
Los *required reviewers* de un environment solo existen en repos públicos (o
planes pagos): en un repo privado gratis el deploy no espera aprobación.

## Pista IA: agregá tu servicio al pipeline

Si sumás una carpeta nueva (por ejemplo `mi-modelo/` con su `Dockerfile`,
`requirements.txt`, `tests/` y un `/healthz`), agregala en tres lugares de
`ci.yml`:

1. `test.strategy.matrix.service`: `mi-modelo`.
2. `build.strategy.matrix.include`: `- service: mi-modelo` y `port: <su puerto>`.
3. `publish.strategy.matrix.service`: `mi-modelo`.

La imagen queda como `$AR/mi-modelo:<sha>`. Los `${{ github.sha }}` son
sintaxis de Actions: **no** funcionan en tu terminal (ahí usá `$(git rev-parse HEAD)`).

## Limpieza

Nada que cueste plata. Si querés desarmar OIDC al final de la cursada:
`gcloud iam workload-identity-pools delete github --location=global`.

## Errores frecuentes

| Si ves | Causa | Hacé |
|---|---|---|
| `publish` gris (skipped) | Falta la variable `GCP_PROJECT_ID` | Es lo esperado hasta el paso 4 |
| `::error::GCP_WORKLOAD_IDENTITY_PROVIDER must be the full name` | Pusiste solo `github-provider` o el id del proyecto en vez del número | Copiá la salida del `describe` del paso 3 |
| `IAM Service Account Credentials API has not been used` | Falta habilitar las APIs | El `gcloud services enable ...` del paso 3 |
| `Permission 'iam.serviceAccounts.getAccessToken' denied` | El binding todavía no propagó, o `attribute.repository` no coincide con tu repo | Esperá 5 min; revisá `<usuario>/<repo>` exacto |
| `denied: Permission "artifactregistry.repositories.uploadArtifacts"` | La cuenta no tiene `artifactregistry.writer` sobre ese repositorio | El `add-iam-policy-binding` del paso 3, en la misma región |
| `name unknown` | `AR_REPOSITORY`/`GCP_REGION` no coinciden con el repositorio de la clase 3 | `gcloud artifacts repositories list` |
| `tag 'v1' is not semver` | El tag no es `vX.Y.Z` | `git tag v1.0.0` |
| `contracts` no corrió con mi push | No tocaste `contracts/` (filtro de paths) | Es lo esperado; con un tag corre siempre |
| `secret BASE_SEPOLIA_DEPLOYER_KEY is empty` | El secret no está en el environment `testnet` | Cargalo en Settings → Environments → testnet |
| No veo la pestaña Actions o no corre nada | El repo es un fork | Creá el repo con **Use this template** |
| `bad substitution` en tu terminal | Pegaste `${{ github.sha }}` en bash | Usá `$(git rev-parse HEAD)` |
