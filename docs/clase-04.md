# Clase 4 — CI/CD con GitHub Actions y OIDC

## Qué mirás de este repo

- `.github/workflows/ci.yml`: test → build → (en `main`) push a Artifact
  Registry, autenticado con Workload Identity Federation (OIDC).
- `.github/workflows/contracts.yml` (ejemplo Blockchain): `forge test` en cada
  PR sobre `contracts/`, y un deploy opcional a testnet en un tag.

## La idea central: OIDC en vez de una clave guardada

`ci.yml` nunca tiene una clave JSON de service account. En su lugar, GitHub
emite un token de identidad de corta duración (OIDC) y GCP confía en él
mediante un Workload Identity Provider. Si el repo se filtra, no hay ninguna
credencial de larga vida que rotar.

Configurás esto como **variables de repositorio** (Settings → Secrets and
variables → Actions → Variables), nunca como texto en el código:

```
GCP_PROJECT_ID
GCP_REGION
GCP_WORKLOAD_IDENTITY_PROVIDER
GCP_SERVICE_ACCOUNT
AR_REPOSITORY
```

## Para probarlo vos (sin GCP)

Los jobs `test` y `build` de `ci.yml` no necesitan ninguna credencial: corren
en cualquier PR.

```bash
make test              # pytest de app/, model/, pow/
make build              # docker build de las tres imágenes
```

## Ejemplo Blockchain: `forge test` como gate

`contracts.yml` corre `forge test` sobre `contracts/` en cada PR que toque
esa carpeta. El deploy a Base Sepolia (clase 7) sólo ocurre en un tag, contra
un entorno de GitHub con aprobación manual, y usa una clave de deployer que
vive como *secret*, nunca commiteada.

```bash
cd contracts
forge test -vv
```
