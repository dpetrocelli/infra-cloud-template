# Clase 7: IA (Vertex AI, Ollama, vast.ai) · Blockchain (Layer 2, Base Sepolia)

## Objetivo

Cada pista lleva su artefacto a "su" nube y lo mide.

- **IA**: el servidor de `model/` es el *stand-in* local de un endpoint de
  inferencia. Lo medís en tu laptop y comparás con una opción administrada
  (Vertex AI / Cloud Run), una autogestionada (Ollama en una VM) o una GPU
  alquilada (vast.ai).
- **BC**: el mismo contrato (`contracts/src/Counter.sol`), desplegado primero en
  Anvil local y después en un rollup L2 de prueba (Base Sepolia).

Lo que se entrega es lo que pide el lab de Moodle de tu pista; esta guía te
deja todo lo del repo funcionando para hacerlo.

## Prerrequisitos

- [ ] `make doctor` sin `[FAIL]`, en la raíz del repo.
- [ ] IA: `make build-model` (imagen `model:local`).
- [ ] BC: nada más (Foundry corre en Docker). Para testnet: una billetera de
      prueba (MetaMask) con ETH de Base Sepolia.

## Pista IA

### 1. El servidor y su contrato

```bash
make test-model                    # 6 passed
docker run -d --name model -p 8081:8081 model:local
until curl -sf localhost:8081/healthz; do sleep 1; done; echo
curl -s -X POST localhost:8081/predict -H 'Content-Type: application/json' \
  -d '{"features": [6.7, 3.0, 5.2, 2.3]}'; echo
```

Esperado: `{"status":"ok"}` y `{"class":"virginica","confidence":0.9...}`.
`GET /` lista los endpoints y `/docs` muestra la API. El modelo se carga **al
arrancar**: `/healthz` da 503 hasta que está listo, así que el primer
`/predict` ya no paga la carga.

### 2. Medilo

`hey` genera carga y te da la distribución de latencias. Sin instalarlo:

```bash
docker run --rm --network host williamyeh/hey -n 2000 -c 20 -m POST \
  -H 'Content-Type: application/json' -d '{"features":[5.1,3.5,1.4,0.2]}' \
  http://localhost:8081/predict
```

(`--network host` funciona en Linux y WSL; en macOS usá
`http://host.docker.internal:8081/predict` sin `--network host`.)
Mirá `Requests/sec` y la línea `95% in ...`: esa es tu p95. Para comparar con
la nube anotá también la primera request en frío
(`curl -w '%{time_total}\n' -o /dev/null -s ...` justo después de arrancar).

Limpieza: `docker rm -f model`.

### 3. (Opcional) En el cluster local

```bash
make k3d-up && make k3d-images
helm upgrade --install model helm/charts/model -f helm/charts/model/values-k3s.yaml --wait
kubectl port-forward svc/model 18081:8081          # otra terminal
curl -s -X POST localhost:18081/predict -H 'Content-Type: application/json' -d '{"features":[5.1,3.5,1.4,0.2]}'
```

> ### En la nube (IA)
>
> **Cloud Run** (lo más directo para este contenedor):
>
> ```bash
> export PROJECT_ID="mi-proyecto-123" REGION="southamerica-east1"
> export AR="${REGION}-docker.pkg.dev/${PROJECT_ID}/infra-cloud-template"
> docker tag model:local "$AR/model:v1" && docker push "$AR/model:v1"
> gcloud run deploy model-server --image="$AR/model:v1" --region="$REGION" --port=8081 --allow-unauthenticated
> URL=$(gcloud run services describe model-server --region="$REGION" --format='value(status.url)')
> curl -s -X POST "$URL/predict" -H 'Content-Type: application/json' -d '{"features":[5.1,3.5,1.4,0.2]}'
> ```
>
> **Vertex AI**: un *custom container* de Vertex recibe `{"instances": [...]}`
> en la ruta que le indiques y responde `{"predictions": [...]}`; nuestro
> `/predict` usa `{"features": [...]}`. Para usar Vertex tal cual hay que
> agregar esa ruta adaptadora en `model/serve.py`. Por eso para comparar te
> recomendamos Cloud Run.
>
> **Ollama en una VM**: usá **e2-medium** o más (`llama3.2:1b` ocupa ~1,5 GB de
> RAM), y recordá que Ollama tiene otro contrato (`/api/generate`) y es otro tipo
> de modelo: la comparación de latencia no es "manzana con manzana". El firewall
> del curso solo abre el 8080: medí desde la VM contra `localhost`, o con un
> túnel (`gcloud compute ssh <vm> -- -L 11434:localhost:11434`), o agregá el
> puerto con `extra_ports` en `terraform/modules/network`.
>
> **vast.ai**: seguí la herramienta que indica el lab. El contenedor es el mismo;
> lo que cambia es la máquina.
>
> Al terminar: `gcloud run services delete model-server --region="$REGION"` y
> apagá/borrá cualquier VM o instancia con GPU (se cobran por hora).

## Pista BC

### 1. Tests del contrato

```bash
make test-contracts        # usa la imagen de Foundry si no tenés forge
```

Esperado: `5 tests passed, 0 failed`.

### 2. Deploy en Anvil local

```bash
make compose-anvil-up
docker compose -f compose/docker-compose.anvil.yml logs anvil | sed -n '/Private Keys/,/Wallet/p' | head -4
```

Esas claves son **públicas y solo sirven en Anvil**. Usamos la (0):

```bash
export DEPLOYER_PRIVATE_KEY=0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80
cd contracts
forge script script/Deploy.s.sol --rpc-url http://localhost:8545 \
  --private-key "$DEPLOYER_PRIVATE_KEY" --broadcast
cd ..
```

Sin Foundry instalado, el mismo comando en Docker (Linux/WSL):

```bash
docker run --rm --network host -u "$(id -u):$(id -g)" -e HOME=/tmp -v "$PWD/contracts:/w" -w /w \
  --entrypoint forge ghcr.io/foundry-rs/foundry:stable \
  script script/Deploy.s.sol --rpc-url http://localhost:8545 --private-key "$DEPLOYER_PRIVATE_KEY" --broadcast
```

Esperado: `Counter deployed at: 0x5FbDB2315678afecb367f032d93F642f64180aa3` y
`ONCHAIN EXECUTION COMPLETE & SUCCESSFUL.` (en un Anvil recién creado la
dirección es siempre esa).

### 3. Usalo

```bash
DC="docker compose -f compose/docker-compose.anvil.yml"
ADDR=0x5FbDB2315678afecb367f032d93F642f64180aa3
$DC exec anvil cast send $ADDR "increment()" --private-key "$DEPLOYER_PRIVATE_KEY" --rpc-url http://localhost:8545
$DC exec anvil cast call $ADDR "number()(uint256)" --rpc-url http://localhost:8545      # 1
$DC exec anvil cast logs --address $ADDR --from-block 0 --rpc-url http://localhost:8545 # el evento NumberChanged
```

`cast logs` es la idea de un *indexer*: leer los eventos del contrato en vez de
consultar su estado. Como el compose guarda la cadena (clase 3),
`make compose-anvil-down && make compose-anvil-up` y el `cast call` sigue dando 1.

> ### En la nube (testnet L2)
>
> | Red | chainId | RPC público |
> |---|---|---|
> | Base Sepolia (L2) | 84532 | `https://sepolia.base.org` |
> | Sepolia (L1) | 11155111 | `https://ethereum-sepolia-rpc.publicnode.com` |
>
> (`https://rpc.sepolia.org` ya no responde.) ETH de prueba: los faucets que
> lista `https://docs.base.org/tools/network-faucets`.
>
> Deploy manual, con **tu** clave de testnet (nunca una de mainnet, nunca en un archivo del repo):
>
> ```bash
> read -rs DEPLOYER_PRIVATE_KEY && export DEPLOYER_PRIVATE_KEY   # pegala y Enter; no se ve
> cd contracts
> forge script script/Deploy.s.sol --rpc-url https://sepolia.base.org \
>   --private-key "$DEPLOYER_PRIVATE_KEY" --broadcast
> ```
>
> Buscá la dirección en `https://sepolia.basescan.org` y compará gas y tiempo de
> confirmación con Sepolia. Por pipeline: el job `deploy-testnet` de
> `contracts.yml` hace lo mismo con un tag `vX.Y.Z` (ver clase 4: environment
> `testnet`, secret `BASE_SEPOLIA_DEPLOYER_KEY`, variable `BASE_SEPOLIA_RPC_URL`).
>
> Un rollup *optimistic* (Base) asume que los lotes son válidos y solo los
> disputa si alguien presenta una prueba de fraude dentro de una ventana de
> desafío; un rollup *ZK* prueba cada lote antes de aceptarlo. Comparalos en
> [L2Beat](https://l2beat.com).

## Limpieza

```bash
docker rm -f model 2>/dev/null
make compose-anvil-reset
rm -rf contracts/broadcast contracts/cache contracts/out
unset DEPLOYER_PRIVATE_KEY
```

## Errores frecuentes

| Si ves | Causa | Hacé |
|---|---|---|
| `Error: Failed to decode private key` | `$DEPLOYER_PRIVATE_KEY` vacía | `export DEPLOYER_PRIVATE_KEY=...` en la misma terminal |
| `Connection refused` en `forge script` | Anvil no está corriendo o el RPC es otro | `make compose-anvil-up`; `--rpc-url http://localhost:8545` |
| `contract ... does not have any code` | Anvil se reinició sin estado | Usá el compose del repo (persiste); redeployá |
| `insufficient funds` en testnet | La cuenta no tiene ETH de Base Sepolia | Faucet |
| `forge: command not found` | Foundry no instalado | `make test-contracts` o el comando con Docker de arriba |
| `port is already allocated` | Quedó un contenedor (`model`, el compose de otra clase) | `docker ps` y `docker rm -f ...` / `make compose-down` |
| `hey` se cuelga contra la VM | El firewall solo abre 8080 | Medí desde la VM o con un túnel SSH |
| `ImagePullBackOff` del modelo en k3s | No importaste la imagen o usaste `values.yaml` | `make k3d-images` y `-f values-k3s.yaml` |
| Pods evicted (`ephemeral-storage`) | Disco casi lleno | Ver la clase 5 |
| `rpc.sepolia.org` no responde | Ese RPC público dejó de funcionar | El de publicnode de la tabla |
